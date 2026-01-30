import json
import os
import logging
from huggingface_hub import InferenceClient

# Setting up Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLMEngine")

# We use Qwen 2.5 Coder because it is great at JSON handling and coding
# and is available for free in the Hugging Face Inference API.
REPO_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"

# Attempt to import only if we are in Colab
try:
  from google.colab import userdata
  IN_COLAB = True
except ImportError:
  IN_COLAB = False

class LLMEngine:
  def __init__(self, api_token=None):
    """
    Initializes the client. It tries to find the HF_TOKEN from Colab Secrets or from environment variables.
    """
    self.token = api_token

    if not self.token and IN_COLAB:
      try:
        self.token = userdata.get('HF_TOKEN')
      except Exception:
        logging.warning("Could not load HF_TOKEN from Colab secrets.")
    
    if not self.token:
      self.token = os.getenv('HF_TOKEN')
    
    if not self.token:
      raise ValueError("No API Token found! Pass it as an argument or set HF_TOKEN in secrets.")

    self.client = InferenceClient(model=REPO_ID, token=self.token)
  
  def parse_response(self, response_text):
    """
    It cleans up the LLM response and returns a Python Dictionary.
    """
    try:
      # Markdown removal if exists
      clean_text = response_text.strip()

      if "```json" in clean_text:
        clean_text = clean_text.split("```json")[1].split("```")[0]
      elif "```" in clean_text:
        clean_text = clean_text.split("```")[1].split("```")[0]
      return json.loads(clean_text)

    except json.JSONDecodeError:
      logging.error(f"JSON PARSING ERROR. Raw text: {response_text}")
      # Fallback: Return a special command for the FSM to handle.
      return {
        "thought": "Failed to parse JSON. I need to retry.",
        "action_type": "TRANSITION",
        "target": "ADJUSTMENT",
        "params": {"error": "Invalid JSON format received from LLM"}
      }

  def get_decision(self, system_prompt, history):
    """
    Sends the prompt and history to LLM.
    """
    messages = [{"role": "system", "content": system_prompt}]

    # Sliding Window: We only keep the last 6 messages for economy and to avoid confusing the model with old data.
    for msg in history[-6:]:
      messages.append(msg)
    
    try:
      response = self.client.chat_completion(
        messages=messages,
        max_tokens=600, # Enough for analytical thought + JSON
        temperature=0.1 # Low to keep the JSON stable (could amp this to 0.2, we'll see)
      )

      raw_content = response.choices[0].message.content
      return self.parse_response(raw_content)
    
    except Exception as e:
      logging.error(f"API ERROR: {e}")
      # Emergency response if the internet or API goes down
      return {
        "thought": "API Connection Error. Terminating safely.",
        "action_type": "TRANSITION",
        "target": "TERMINATED",
        "params": {"error": str(e)}
      }