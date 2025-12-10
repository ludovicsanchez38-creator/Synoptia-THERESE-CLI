"""
Base class for LLM providers.

Abstraction permettant de supporter plusieurs backends :
- Mistral API (cloud)
- Ollama (local)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Any


@dataclass
class StreamChunk:
    """Un chunk de streaming."""
    content: str | None = None
    tool_calls: list[dict] | None = None
    usage: dict | None = None  # {"prompt_tokens": int, "completion_tokens": int}
    finish_reason: str | None = None


class ProviderBase(ABC):
    """Interface abstraite pour tous les providers LLM."""

    name: str = "base"
    supports_tools: bool = False
    supports_vision: bool = False
    supports_thinking: bool = False

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict],
        model: str,
        tools: list[dict] | None = None,
    ) -> Iterator[StreamChunk]:
        """
        Streaming synchrone de la réponse.

        Args:
            messages: Liste de messages au format {"role": str, "content": str}
            model: Nom du modèle à utiliser
            tools: Schémas des outils (function calling)

        Yields:
            StreamChunk avec content et/ou tool_calls
        """
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """Liste les modèles disponibles."""
        ...

    def is_available(self) -> bool:
        """Vérifie si le provider est disponible."""
        return True

    def get_default_model(self) -> str:
        """Retourne le modèle par défaut pour ce provider."""
        models = self.list_models()
        return models[0] if models else ""
