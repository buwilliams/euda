from typing import Any, Dict

import anthropic

from .base import BaseLLMClient, LLMClientError, LLMResponse


class AnthropicClient(BaseLLMClient):
    def call(self, system_prompt: str, prompt: str) -> LLMResponse:
        api_key = self.provider_config.get("api_key")
        if not api_key:
            raise LLMClientError("Anthropic API key is not set in config")
        base_url = self.provider_config.get("base_url")
        headers = {}
        if self.provider_config.get("anthropic_version"):
            headers["anthropic-version"] = self.provider_config["anthropic_version"]
        client_kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if headers:
            client_kwargs["default_headers"] = headers
        client = anthropic.Anthropic(**client_kwargs)
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt
        try:
            message = client.messages.create(**payload)
        except Exception as exc:
            raise LLMClientError(f"Anthropic error: {exc}") from exc
        text = "".join(
            block.text
            for block in message.content
            if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        )
        usage = getattr(message, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage else None
        output_tokens = getattr(usage, "output_tokens", None) if usage else None
        total_tokens = None
        if input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        return LLMResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
