"""
Multi-model LLM provider abstraction for Tastyz Bakery.

Supports OpenAI, Google Gemini, Anthropic Claude, Grok (xAI), and Ollama (local).
Reads provider-specific API keys from Django settings / .env.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_llm(
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
    max_tokens: int = 1024,
):
    """
    Return a LangChain Chat LLM instance for the given provider.

    Args:
        provider: 'openai', 'google', 'anthropic', 'grok', or 'ollama'
        model: model identifier string
        temperature, top_p, frequency_penalty, presence_penalty, max_tokens:
            standard LLM parameters

    Returns:
        A LangChain BaseChatModel instance.
    """
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=model,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            max_tokens=max_tokens,
        )

    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured in settings/.env")

        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_output_tokens=max_tokens,
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured in settings/.env")

        return ChatAnthropic(
            anthropic_api_key=api_key,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )

    elif provider == "grok":
        # Grok (xAI) uses an OpenAI-compatible API endpoint
        from langchain_openai import ChatOpenAI

        api_key = getattr(settings, "GROK_API_KEY", "")
        if not api_key:
            raise ValueError("GROK_API_KEY not configured in settings/.env")

        return ChatOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
            model=model,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            max_tokens=max_tokens,
        )

    elif provider == "ollama":
        # Ollama runs locally — no API key needed, just a base URL
        from langchain_ollama import ChatOllama

        base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(
            base_url=base_url,
            model=model,
            temperature=temperature,
            top_p=top_p,
            num_predict=max_tokens,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_from_settings(llm_settings) -> object:
    """
    Build an LLM instance from an LLMSettings model instance.
    """
    return get_llm(
        provider=llm_settings.provider,
        model=llm_settings.model_name,
        temperature=llm_settings.temperature,
        top_p=llm_settings.top_p,
        frequency_penalty=llm_settings.frequency_penalty,
        presence_penalty=llm_settings.presence_penalty,
        max_tokens=llm_settings.max_tokens,
    )


def get_available_providers() -> dict:
    """Return dict of available providers with their configured status."""
    providers = {
        "openai": {
            "name": "OpenAI",
            "configured": bool(getattr(settings, "OPENAI_API_KEY", "")),
            "icon": "bi-lightning-charge",
        },
        "google": {
            "name": "Google Gemini",
            "configured": bool(getattr(settings, "GEMINI_API_KEY", "")),
            "icon": "bi-google",
        },
        "anthropic": {
            "name": "Anthropic Claude",
            "configured": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
            "icon": "bi-robot",
        },
        "grok": {
            "name": "Grok (xAI)",
            "configured": bool(getattr(settings, "GROK_API_KEY", "")),
            "icon": "bi-stars",
        },
        "ollama": {
            "name": "Ollama (Local)",
            "configured": True,  # Always available if Ollama server is running
            "icon": "bi-pc-display",
        },
    }
    return providers
