from typing import Any, Dict

from src.providers import AnthropicClient, LLMClientError, OpenAIClient, XAIClient


def get_llm_client(config: Dict[str, Any]):
    provider = config.get("provider")
    providers = config.get("providers") or {}
    provider_config = providers.get(provider, {})
    provider_config = dict(provider_config)
    api_keys = config.get("api_keys") or {}
    provider_config["api_key"] = api_keys.get(provider)
    model = config.get("model")
    if not provider:
        raise LLMClientError("Config is missing provider")
    if provider not in providers:
        available = ", ".join(sorted(providers.keys()))
        raise LLMClientError(f"Unknown provider '{provider}'. Available: {available}")
    if not model:
        raise LLMClientError("Config is missing model")
    models = provider_config.get("models") or {}
    if model not in models:
        available = ", ".join(sorted(models.keys()))
        raise LLMClientError(
            f"Unknown model '{model}' for provider '{provider}'. Available: {available}"
        )
    if provider == "openai":
        return OpenAIClient(model, provider_config)
    if provider == "anthropic":
        return AnthropicClient(model, provider_config)
    if provider == "xai":
        return XAIClient(model, provider_config)
    raise LLMClientError(f"Unsupported provider: {provider}")
