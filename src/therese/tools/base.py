"""Classe de base pour les outils THERESE."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Résultat de l'exécution d'un outil."""

    success: bool
    output: str
    error: str | None = None

    def to_string(self) -> str:
        """Convertit le résultat en chaîne pour Mistral."""
        if self.success:
            return self.output
        return f"Erreur: {self.error}\n{self.output}" if self.output else f"Erreur: {self.error}"


class Tool(ABC):
    """Classe de base abstraite pour tous les outils."""

    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Exécute l'outil avec les paramètres donnés."""
        ...

    def to_mistral_schema(self) -> dict:
        """Convertit l'outil en schéma Mistral pour function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __repr__(self) -> str:
        return f"<Tool {self.name}>"
