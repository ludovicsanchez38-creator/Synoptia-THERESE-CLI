"""Outil de lecture de fichiers."""

from pathlib import Path
from typing import Any

from .base import Tool, ToolResult


class ReadTool(Tool):
    """Lit le contenu d'un fichier."""

    name = "read_file"
    description = (
        "Lit le contenu d'un fichier. Retourne le contenu avec les numéros de ligne. "
        "Supporte offset et limit pour les gros fichiers."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Chemin absolu ou relatif du fichier à lire",
            },
            "offset": {
                "type": "integer",
                "description": "Ligne de départ (1-indexed). Par défaut: 1",
            },
            "limit": {
                "type": "integer",
                "description": "Nombre de lignes à lire. Par défaut: toutes",
            },
        },
        "required": ["file_path"],
    }

    async def execute(
        self,
        file_path: str,
        offset: int = 1,
        limit: int | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Lit le fichier et retourne son contenu."""
        try:
            path = Path(file_path).expanduser().resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Le fichier n'existe pas: {path}",
                )

            if not path.is_file():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Le chemin n'est pas un fichier: {path}",
                )

            # Vérifier la taille du fichier
            size = path.stat().st_size
            if size > 10 * 1024 * 1024:  # 10 MB
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Fichier trop volumineux ({size / 1024 / 1024:.1f} MB). Utilisez offset/limit.",
                )

            # Lire le fichier
            content = path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            # Appliquer offset et limit
            start = max(0, offset - 1)
            end = start + limit if limit else len(lines)
            selected_lines = lines[start:end]

            # Formater avec numéros de ligne
            output_lines = []
            for i, line in enumerate(selected_lines, start=start + 1):
                # Tronquer les lignes très longues
                if len(line) > 500:
                    line = line[:500] + "... [tronqué]"
                output_lines.append(f"{i:6d}\t{line}")

            output = "\n".join(output_lines)

            # Info sur le fichier
            header = f"# {path} ({len(lines)} lignes)\n"
            if start > 0 or end < len(lines):
                header += f"# Affichage: lignes {start + 1}-{min(end, len(lines))}\n"

            return ToolResult(success=True, output=header + output)

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
                error=f"Erreur de lecture: {e}",
            )
