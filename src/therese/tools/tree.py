"""Outil Tree : affiche la structure des répertoires."""

import fnmatch
from pathlib import Path
from typing import Any

from .base import Tool, ToolResult


class TreeTool(Tool):
    """Affiche l'arborescence d'un répertoire."""

    name = "tree"
    description = (
        "Affiche la structure arborescente d'un répertoire. "
        "Utile pour comprendre l'organisation d'un projet."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Chemin du répertoire. Par défaut: répertoire courant",
            },
            "max_depth": {
                "type": "integer",
                "description": "Profondeur maximale. Par défaut: 3",
            },
            "show_hidden": {
                "type": "boolean",
                "description": "Afficher les fichiers cachés. Par défaut: false",
            },
            "dirs_only": {
                "type": "boolean",
                "description": "Afficher uniquement les répertoires. Par défaut: false",
            },
        },
        "required": [],
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
        ".DS_Store",
        "*.pyc",
        ".coverage",
        "htmlcov",
        ".next",
        ".nuxt",
        "target",  # Rust
        "vendor",  # Go
    ]

    def _should_ignore(self, name: str) -> bool:
        """Vérifie si un nom doit être ignoré."""
        for pattern in self.IGNORE_PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    def _build_tree(
        self,
        path: Path,
        prefix: str = "",
        max_depth: int = 3,
        current_depth: int = 0,
        show_hidden: bool = False,
        dirs_only: bool = False,
    ) -> list[str]:
        """Construit l'arborescence récursivement."""
        if current_depth >= max_depth:
            return []

        lines = []

        try:
            entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return [f"{prefix}[permission denied]"]

        # Filtrer
        filtered = []
        for entry in entries:
            if not show_hidden and entry.name.startswith("."):
                continue
            if self._should_ignore(entry.name):
                continue
            if dirs_only and not entry.is_dir():
                continue
            filtered.append(entry)

        for i, entry in enumerate(filtered):
            is_last = i == len(filtered) - 1
            connector = "└── " if is_last else "├── "
            extension = "    " if is_last else "│   "

            if entry.is_dir():
                lines.append(f"{prefix}{connector}📁 {entry.name}/")
                lines.extend(
                    self._build_tree(
                        entry,
                        prefix + extension,
                        max_depth,
                        current_depth + 1,
                        show_hidden,
                        dirs_only,
                    )
                )
            else:
                # Icône selon extension
                icon = self._get_icon(entry.suffix)
                lines.append(f"{prefix}{connector}{icon} {entry.name}")

        return lines

    def _get_icon(self, suffix: str) -> str:
        """Retourne une icône selon l'extension."""
        icons = {
            ".py": "🐍",
            ".js": "📜",
            ".ts": "📘",
            ".tsx": "⚛️",
            ".jsx": "⚛️",
            ".json": "📋",
            ".md": "📝",
            ".txt": "📄",
            ".yaml": "⚙️",
            ".yml": "⚙️",
            ".toml": "⚙️",
            ".html": "🌐",
            ".css": "🎨",
            ".scss": "🎨",
            ".sql": "🗃️",
            ".sh": "🔧",
            ".rs": "🦀",
            ".go": "🐹",
            ".java": "☕",
            ".rb": "💎",
            ".php": "🐘",
            ".swift": "🍎",
            ".kt": "🎯",
            ".vue": "💚",
            ".svelte": "🔥",
            ".env": "🔐",
            ".lock": "🔒",
            ".png": "🖼️",
            ".jpg": "🖼️",
            ".svg": "🎨",
            ".gif": "🖼️",
        }
        return icons.get(suffix.lower(), "📄")

    async def execute(
        self,
        path: str | None = None,
        max_depth: int = 3,
        show_hidden: bool = False,
        dirs_only: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Affiche l'arborescence."""
        try:
            base_path = Path(path or ".").expanduser().resolve()

            if not base_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Le répertoire n'existe pas: {base_path}",
                )

            if not base_path.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Le chemin n'est pas un répertoire: {base_path}",
                )

            lines = [f"📁 {base_path.name}/"]
            lines.extend(
                self._build_tree(
                    base_path,
                    "",
                    max_depth,
                    0,
                    show_hidden,
                    dirs_only,
                )
            )

            # Compter
            file_count = sum(1 for line in lines if not line.rstrip().endswith("/"))
            dir_count = sum(1 for line in lines if line.rstrip().endswith("/"))

            lines.append("")
            lines.append(f"📊 {dir_count} répertoires, {file_count - 1} fichiers")

            return ToolResult(success=True, output="\n".join(lines))

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur: {e}",
            )
