import json
import re
import logging
from huggingface_hub import InterfaceClient

REPO_ID = ""

class LLMEngine:
  def __init__(self, api_token):
    """
    Initializes the Hugging Face communication client.
    """