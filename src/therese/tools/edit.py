"""Outil d'édition de fichiers."""

from pathlib import Path
from typing import Any

from .base import Tool, ToolResult


class EditTool(Tool):
    """Édite un fichier en remplaçant une chaîne par une autre."""

    name = "edit_file"
    description = (
        "Édite un fichier en remplaçant old_string par new_string. "
        "La chaîne old_string doit être unique dans le fichier (sinon utilisez replace_all=true)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Chemin du fichier à éditer",
            },
            "old_string": {
                "type": "string",
                "description": "Chaîne à remplacer (doit être exacte)",
            },
            "new_string": {
                "type": "string",
                "description": "Nouvelle chaîne",
            },
            "replace_all": {
                "type": "boolean",
                "description": "Remplacer toutes les occurrences. Par défaut: false",
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    }

    async def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Édite le fichier."""
        try:
            path = Path(file_path).expanduser().resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Le fichier n'existe pas: {path}",
                )

            content = path.read_text(encoding="utf-8")

            # Compter les occurrences
            count = content.count(old_string)

            if count == 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Chaîne non trouvée dans {path}:\n{old_string[:200]}",
                )

            if count > 1 and not replace_all:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Chaîne trouvée {count} fois. Utilisez replace_all=true ou soyez plus spécifique.",
                )

            # Effectuer le remplacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
            else:
                new_content = content.replace(old_string, new_string, 1)

            # Écrire le fichier modifié
            path.write_text(new_content, encoding="utf-8")

            return ToolResult(
                success=True,
                output=f"Fichier modifié: {path}\n  - {count} remplacement(s) effectué(s)",
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
                error=f"Erreur d'édition: {e}",
            )
