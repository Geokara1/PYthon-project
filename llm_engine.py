import json
import re
import logging
from huggingface_hub import InterfaceClient

# We use Qwen 2.5 Coder because it is great at JSON handling and coding
# and is available for free in the Hugging Face Inference API.

REPO_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"

class LLMEngine:
  def __init__(self, api_token):
    """
    Initializes the Hugging Face communication client.
    """
    if not api_token:
      raise ValueError("API Token is missing! Please provide a valid Hugging Face token.")
    
    self.client = InterfaceClient(model=REPO_ID, token=api_token)
  
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
      
      # Parsing in Python Dict
      return json.loads(clean_text)

    except json.JSONDecodeError:
      logging.error(f"JSON PARSING ERROR. Raw text received: {response_text}")
      # Fallback: Return a special command for the FSM to handle.
      return {
        "thought": "Failed to parse JSON response. I need to retry or terminate.",
        "action_type": "TRANSITION",
        "target": "ADJUSTMENT", # Safety Fallback
        "params": {"error": "Invalid JSON format"}
      }

  def get_decision(self, system_prompt, history):
    """
    It sends the history to the LLM and makes a decision.
    Manages the Context Window (Sliding Window).
    """
    messages = [{"role": "system", "content": system_prompt}]

    # CONTEXT WINDOW MANAGEMENT !!!
    # We only keep the last 6 messages to avoid filling up the memory.
    # and not to be charged too many tokens.
    sliding_window_history = history[-6:]

    for msg in sliding_window_history:
      messages.append(msg)
    
    try:
      # API Call
      response = self.client.chat_completion(
        messages=messages,
        max_tokens=500, # Enough for JSON files, not too much
        temperature=0.1 # Low in order to be deterministic (stable) (could amp this to 0.2, we'll see)
      )

      raw_content = response.choices[0].message.content
      return self.parse_response(raw_content)
    
    except Exception as e:
      logging.error(f"API CONNECTION ERROR: {e}")
      # Emergency response if the internet or API goes down
      return {
        "thought": "API Error. Initiating emergency termination.",
        "action_type": "TRANSITION",
        "target": "TERMINATED",
        "params": {}
      }