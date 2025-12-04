"""Outil d'écriture de fichiers."""

from pathlib import Path
from typing import Any

from .base import Tool, ToolResult


class WriteTool(Tool):
    """Écrit du contenu dans un fichier."""

    name = "write_file"
    description = (
        "Écrit du contenu dans un fichier. Crée le fichier et les répertoires parents si nécessaire. "
        "ATTENTION: Écrase le contenu existant."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Chemin du fichier à écrire",
            },
            "content": {
                "type": "string",
                "description": "Contenu à écrire dans le fichier",
            },
        },
        "required": ["file_path", "content"],
    }

    async def execute(
        self,
        file_path: str,
        content: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Écrit le contenu dans le fichier."""
        try:
            path = Path(file_path).expanduser().resolve()

            # Créer les répertoires parents si nécessaire
            path.parent.mkdir(parents=True, exist_ok=True)

            # Écrire le fichier
            path.write_text(content, encoding="utf-8")

            lines = content.count("\n") + 1
            size = len(content.encode("utf-8"))

            return ToolResult(
                success=True,
                output=f"Fichier écrit: {path}\n  - {lines} lignes\n  - {size} octets",
            )

        except PermissionError:
            return ToolResult(
                success=False,
                output="",
                error=f"Permission refusée: {file_path}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur d'écriture: {e}",
            )
