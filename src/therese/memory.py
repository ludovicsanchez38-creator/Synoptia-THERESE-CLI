"""
Système de mémoire persistante pour THERESE CLI.

Inspiré de CLAUDE.md - fichier de mémoire projet.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ProjectMemory:
    """Mémoire d'un projet."""

    # Informations projet
    name: str = ""
    description: str = ""
    language: str = ""
    frameworks: list[str] = field(default_factory=list)

    # Conventions
    code_style: str = ""
    naming_conventions: str = ""
    file_structure: str = ""

    # Contexte technique
    key_files: list[str] = field(default_factory=list)
    important_patterns: list[str] = field(default_factory=list)
    gotchas: list[str] = field(default_factory=list)

    # Historique
    recent_changes: list[dict] = field(default_factory=list)
    common_tasks: list[str] = field(default_factory=list)

    # Personnalisation
    user_preferences: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Exporte la mémoire en Markdown (format THERESE.md)."""
        lines = [
            "# THERESE.md - Mémoire Projet",
            "",
            f"> Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
        ]

        if self.name or self.description:
            lines.append("## 📁 Projet")
            if self.name:
                lines.append(f"**Nom:** {self.name}")
            if self.description:
                lines.append(f"**Description:** {self.description}")
            if self.language:
                lines.append(f"**Langage:** {self.language}")
            if self.frameworks:
                lines.append(f"**Frameworks:** {', '.join(self.frameworks)}")
            lines.append("")

        if self.code_style or self.naming_conventions or self.file_structure:
            lines.append("## 📝 Conventions")
            if self.code_style:
                lines.append(f"**Style de code:** {self.code_style}")
            if self.naming_conventions:
                lines.append(f"**Nommage:** {self.naming_conventions}")
            if self.file_structure:
                lines.append(f"**Structure:** {self.file_structure}")
            lines.append("")

        if self.key_files:
            lines.append("## 🔑 Fichiers clés")
            for f in self.key_files:
                lines.append(f"- `{f}`")
            lines.append("")

        if self.important_patterns:
            lines.append("## 🎯 Patterns importants")
            for p in self.important_patterns:
                lines.append(f"- {p}")
            lines.append("")

        if self.gotchas:
            lines.append("## ⚠️ Pièges à éviter")
            for g in self.gotchas:
                lines.append(f"- {g}")
            lines.append("")

        if self.common_tasks:
            lines.append("## 🔄 Tâches courantes")
            for t in self.common_tasks:
                lines.append(f"- {t}")
            lines.append("")

        if self.recent_changes:
            lines.append("## 📅 Changements récents")
            for change in self.recent_changes[-5:]:
                lines.append(f"- [{change.get('date', 'N/A')}] {change.get('description', '')}")
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, content: str) -> "ProjectMemory":
        """Parse un fichier THERESE.md."""
        memory = cls()

        current_section = None
        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("## "):
                current_section = line[3:].lower()
                continue

            if not line or line.startswith("#") or line.startswith(">"):
                continue

            if current_section and "projet" in current_section:
                if line.startswith("**Nom:**"):
                    memory.name = line.split(":", 1)[1].strip()
                elif line.startswith("**Description:**"):
                    memory.description = line.split(":", 1)[1].strip()
                elif line.startswith("**Langage:**"):
                    memory.language = line.split(":", 1)[1].strip()
                elif line.startswith("**Frameworks:**"):
                    memory.frameworks = [f.strip() for f in line.split(":", 1)[1].split(",")]

            elif current_section and "fichiers" in current_section:
                if line.startswith("- "):
                    memory.key_files.append(line[2:].strip("`"))

            elif current_section and "patterns" in current_section:
                if line.startswith("- "):
                    memory.important_patterns.append(line[2:])

            elif current_section and "pièges" in current_section:
                if line.startswith("- "):
                    memory.gotchas.append(line[2:])

            elif current_section and "tâches" in current_section:
                if line.startswith("- "):
                    memory.common_tasks.append(line[2:])

        return memory


class MemoryManager:
    """Gestionnaire de mémoire projet."""

    MEMORY_FILE = "THERESE.md"

    def __init__(self, project_path: Path | None = None):
        self.project_path = project_path or Path.cwd()
        self.memory_file = self.project_path / self.MEMORY_FILE
        self._memory: ProjectMemory | None = None

    @property
    def memory(self) -> ProjectMemory:
        """Charge ou crée la mémoire."""
        if self._memory is None:
            self._memory = self.load()
        return self._memory

    def load(self) -> ProjectMemory:
        """Charge la mémoire depuis le fichier."""
        if self.memory_file.exists():
            try:
                content = self.memory_file.read_text()
                return ProjectMemory.from_markdown(content)
            except Exception:
                pass
        return ProjectMemory()

    def save(self) -> None:
        """Sauvegarde la mémoire."""
        if self._memory:
            self.memory_file.write_text(self._memory.to_markdown())

    def add_change(self, description: str) -> None:
        """Ajoute un changement récent."""
        self.memory.recent_changes.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": description,
        })
        # Garder les 20 derniers
        self.memory.recent_changes = self.memory.recent_changes[-20:]
        self.save()

    def add_key_file(self, file_path: str) -> None:
        """Ajoute un fichier clé."""
        if file_path not in self.memory.key_files:
            self.memory.key_files.append(file_path)
            self.save()

    def add_pattern(self, pattern: str) -> None:
        """Ajoute un pattern important."""
        if pattern not in self.memory.important_patterns:
            self.memory.important_patterns.append(pattern)
            self.save()

    def add_gotcha(self, gotcha: str) -> None:
        """Ajoute un piège à éviter."""
        if gotcha not in self.memory.gotchas:
            self.memory.gotchas.append(gotcha)
            self.save()

    def get_context(self) -> str:
        """Retourne le contexte mémoire pour le prompt."""
        if not self.memory_file.exists():
            return ""

        return f"""
## Mémoire projet (THERESE.md)

{self.memory.to_markdown()}
"""

    def update_from_detection(self, project_info: dict) -> None:
        """Met à jour la mémoire depuis la détection de projet."""
        self.memory.name = project_info.get("name", self.memory.name)
        self.memory.language = project_info.get("language", self.memory.language)
        self.memory.frameworks = project_info.get("frameworks", self.memory.frameworks)
        self.save()


# Instance globale
memory_manager: MemoryManager | None = None


def get_memory_manager(project_path: Path | None = None) -> MemoryManager:
    """Retourne le gestionnaire de mémoire."""
    global memory_manager
    if memory_manager is None or (project_path and memory_manager.project_path != project_path):
        memory_manager = MemoryManager(project_path)
    return memory_manager
