from xai_sdk import Client as XAIAPIClient
from xai_sdk.chat import system as xai_system
from xai_sdk.chat import user as xai_user

from .base import BaseLLMClient, LLMClientError, LLMResponse


class XAIClient(BaseLLMClient):
    def call(self, system_prompt: str, prompt: str) -> LLMResponse:
        api_key = self.provider_config.get("api_key")
        if not api_key:
            raise LLMClientError("xAI API key is not set in config")
        client = XAIAPIClient(api_key=api_key)
        messages = []
        if system_prompt:
            messages.append(xai_system(system_prompt))
        try:
            if messages:
                chat = client.chat.create(model=self.model, messages=messages)
            else:
                chat = client.chat.create(model=self.model)
            chat.append(xai_user(prompt))
            response = chat.sample()
        except Exception as exc:
            raise LLMClientError(f"xAI error: {exc}") from exc
        text = getattr(response, "content", "") or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage else None
        total_tokens = getattr(usage, "total_tokens", None) if usage else None
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        if input_tokens is None and output_tokens is None and total_tokens is not None:
            input_tokens = total_tokens
            output_tokens = 0
        return LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
