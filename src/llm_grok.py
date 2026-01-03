"""
Grok Provider - xAI's Grok models

xAI's API is OpenAI-compatible, so we extend the OpenAI provider
and just change the base URL and API key.
"""

import os

import openai

from .llm_openai import OpenAIProvider


class GrokProvider(OpenAIProvider):
    """xAI/Grok provider implementation.

    Extends OpenAI provider since xAI uses an OpenAI-compatible API.
    """

    XAI_BASE_URL = "https://api.x.ai/v1"

    def __init__(self):
        # Use XAI_API_KEY env var, pointing to xAI's API endpoint
        self.client = openai.OpenAI(
            api_key=os.environ.get("XAI_API_KEY"),
            base_url=self.XAI_BASE_URL
        )
