"""Outil de recherche dans le contenu des fichiers."""

import fnmatch
import re
from pathlib import Path
from typing import Any

from .base import Tool, ToolResult


class GrepTool(Tool):
    """Recherche de texte dans les fichiers."""

    name = "grep"
    description = (
        "Recherche un pattern (regex) dans le contenu des fichiers. "
        "Similaire à 'grep -r' ou 'rg'. Retourne les lignes correspondantes avec contexte."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Pattern regex à rechercher",
            },
            "path": {
                "type": "string",
                "description": "Fichier ou répertoire à rechercher. Par défaut: répertoire courant",
            },
            "glob": {
                "type": "string",
                "description": "Filtrer par extension (ex: '*.py', '*.ts')",
            },
            "case_insensitive": {
                "type": "boolean",
                "description": "Recherche insensible à la casse. Par défaut: false",
            },
            "context": {
                "type": "integer",
                "description": "Lignes de contexte avant/après. Par défaut: 0",
            },
            "limit": {
                "type": "integer",
                "description": "Nombre maximum de résultats. Par défaut: 50",
            },
        },
        "required": ["pattern"],
    }

    # Extensions de fichiers texte
    TEXT_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", ".txt",
        ".yaml", ".yml", ".toml", ".html", ".css", ".scss", ".sql",
        ".sh", ".bash", ".zsh", ".rs", ".go", ".java", ".c", ".cpp",
        ".h", ".hpp", ".rb", ".php", ".swift", ".kt", ".vue", ".svelte",
    }

    # Dossiers à ignorer
    IGNORE_DIRS = {
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        ".pytest_cache", ".mypy_cache", "dist", "build",
    }

    def _is_text_file(self, path: Path) -> bool:
        """Vérifie si c'est un fichier texte."""
        return path.suffix.lower() in self.TEXT_EXTENSIONS

    def _should_ignore_dir(self, name: str) -> bool:
        """Vérifie si le répertoire doit être ignoré."""
        return name in self.IGNORE_DIRS

    async def execute(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        case_insensitive: bool = False,
        context: int = 0,
        limit: int = 50,
        **kwargs: Any,
    ) -> ToolResult:
        """Recherche le pattern dans les fichiers."""
        try:
            # Compiler le regex
            flags = re.IGNORECASE if case_insensitive else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Pattern regex invalide: {e}",
                )

            base_path = Path(path or ".").expanduser().resolve()

            if not base_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Le chemin n'existe pas: {base_path}",
                )

            results: list[str] = []
            files_searched = 0
            matches_found = 0

            # Collecter les fichiers à rechercher
            if base_path.is_file():
                files = [base_path]
            else:
                files = []
                for file_path in base_path.rglob("*"):
                    # Ignorer les répertoires blacklistés
                    if any(self._should_ignore_dir(p) for p in file_path.parts):
                        continue
                    if not file_path.is_file():
                        continue
                    if not self._is_text_file(file_path):
                        continue
                    if glob and not fnmatch.fnmatch(file_path.name, glob):
                        continue
                    files.append(file_path)

            # Rechercher dans chaque fichier
            for file_path in files:
                if matches_found >= limit:
                    break

                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    lines = content.splitlines()
                    files_searched += 1

                    for i, line in enumerate(lines):
                        if matches_found >= limit:
                            break

                        if regex.search(line):
                            matches_found += 1

                            try:
                                rel_path = file_path.relative_to(base_path)
                            except ValueError:
                                rel_path = file_path

                            # Ajouter le contexte
                            start = max(0, i - context)
                            end = min(len(lines), i + context + 1)

                            result_lines = [f"\n{rel_path}:{i + 1}:"]
                            for j in range(start, end):
                                prefix = ">" if j == i else " "
                                result_lines.append(f"  {prefix} {j + 1}: {lines[j]}")

                            results.append("\n".join(result_lines))

                except (OSError, UnicodeDecodeError):
                    continue

            if not results:
                return ToolResult(
                    success=True,
                    output=f"Aucune correspondance pour '{pattern}' ({files_searched} fichiers recherchés)",
                )

            header = f"# {matches_found} correspondance(s) pour '{pattern}' ({files_searched} fichiers)"
            if matches_found >= limit:
                header += f" [limité à {limit}]"

            return ToolResult(success=True, output=header + "\n" + "\n".join(results))

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur de recherche: {e}",
            )
