from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LLMResponse:
    text: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None


class LLMClientError(RuntimeError):
    pass


class BaseLLMClient:
    def __init__(self, model: str, provider_config: Dict[str, Any]) -> None:
        self.model = model
        self.provider_config = provider_config

    def call(self, system_prompt: str, prompt: str) -> LLMResponse:
        raise NotImplementedError
