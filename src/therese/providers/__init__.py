"""
Providers LLM pour THERESE CLI.

Supporte :
- Mistral API (cloud) - défaut
- Ollama (local) - modèles Mistral locaux
"""

from typing import Literal

from .base import ProviderBase, StreamChunk
from .mistral import MistralProvider
from .ollama import OllamaProvider

__all__ = [
    "ProviderBase",
    "StreamChunk",
    "MistralProvider",
    "OllamaProvider",
    "get_provider",
    "PROVIDERS",
]

ProviderType = Literal["mistral", "ollama"]

PROVIDERS: dict[str, type[ProviderBase]] = {
    "mistral": MistralProvider,
    "ollama": OllamaProvider,
}


def get_provider(
    provider_type: ProviderType = "mistral",
    **kwargs,
) -> ProviderBase:
    """
    Factory pour créer un provider.

    Args:
        provider_type: "mistral" ou "ollama"
        **kwargs: Arguments pour le provider
            - mistral: api_key
            - ollama: base_url

    Returns:
        Instance du provider
    """
    provider_class = PROVIDERS.get(provider_type)
    if not provider_class:
        raise ValueError(f"Provider inconnu: {provider_type}. Options: {list(PROVIDERS.keys())}")

    return provider_class(**kwargs)
