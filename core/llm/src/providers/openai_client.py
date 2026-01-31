from typing import Any, Dict

import openai
from openai import OpenAI

from .base import BaseLLMClient, LLMClientError, LLMResponse


class OpenAIClient(BaseLLMClient):
    def call(self, system_prompt: str, prompt: str) -> LLMResponse:
        api_key = self.provider_config.get("api_key")
        if not api_key:
            raise LLMClientError("OpenAI API key is not set in config")
        base_url = self.provider_config.get("base_url")
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)
        messages: list[Dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            response = client.chat.completions.create(model=self.model, messages=messages)
        except openai.RateLimitError as exc:
            raise LLMClientError(f"OpenAI rate limit: {exc}") from exc
        except openai.APIConnectionError as exc:
            raise LLMClientError(f"OpenAI connection error: {exc}") from exc
        except openai.APIError as exc:
            raise LLMClientError(f"OpenAI API error: {exc}") from exc
        except Exception as exc:
            raise LLMClientError(f"OpenAI error: {exc}") from exc
        content = response.choices[0].message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None
        return LLMResponse(
            text=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
