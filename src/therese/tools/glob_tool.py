"""Outil de recherche de fichiers par pattern glob."""

import fnmatch
from pathlib import Path
from typing import Any

from .base import Tool, ToolResult


class GlobTool(Tool):
    """Recherche de fichiers par pattern glob."""

    name = "glob"
    description = (
        "Recherche des fichiers correspondant à un pattern glob (ex: '**/*.py', 'src/**/*.ts'). "
        "Retourne les chemins des fichiers trouvés, triés par date de modification."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Pattern glob (ex: '**/*.py', 'src/**/*.ts')",
            },
            "path": {
                "type": "string",
                "description": "Répertoire de base pour la recherche. Par défaut: répertoire courant",
            },
            "limit": {
                "type": "integer",
                "description": "Nombre maximum de résultats. Par défaut: 100",
            },
        },
        "required": ["pattern"],
    }

    # Patterns à ignorer
    IGNORE_PATTERNS = [
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "*.egg-info",
    ]

    def _should_ignore(self, path: Path) -> bool:
        """Vérifie si le chemin doit être ignoré."""
        for part in path.parts:
            for pattern in self.IGNORE_PATTERNS:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False

    async def execute(
        self,
        pattern: str,
        path: str | None = None,
        limit: int = 100,
        **kwargs: Any,
    ) -> ToolResult:
        """Recherche les fichiers correspondant au pattern."""
        try:
            base_path = Path(path or ".").expanduser().resolve()

            if not base_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Le répertoire n'existe pas: {base_path}",
                )

            # Collecter les fichiers
            matches: list[tuple[Path, float]] = []

            for file_path in base_path.glob(pattern):
                if file_path.is_file() and not self._should_ignore(file_path):
                    try:
                        mtime = file_path.stat().st_mtime
                        matches.append((file_path, mtime))
                    except OSError:
                        continue

            # Trier par date de modification (plus récent en premier)
            matches.sort(key=lambda x: x[1], reverse=True)

            # Appliquer la limite
            matches = matches[:limit]

            if not matches:
                return ToolResult(
                    success=True,
                    output=f"Aucun fichier trouvé pour le pattern: {pattern}",
                )

            # Formater la sortie
            output_lines = [f"# {len(matches)} fichier(s) trouvé(s) pour '{pattern}'", ""]

            for file_path, _ in matches:
                try:
                    rel_path = file_path.relative_to(base_path)
                except ValueError:
                    rel_path = file_path
                output_lines.append(str(rel_path))

            return ToolResult(success=True, output="\n".join(output_lines))

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur de recherche: {e}",
            )
