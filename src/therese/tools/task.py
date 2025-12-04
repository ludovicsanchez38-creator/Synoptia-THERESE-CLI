"""Outil de gestion des tâches (Todo)."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from .base import Tool, ToolResult


@dataclass
class Task:
    """Une tâche."""

    id: int
    content: str
    status: Literal["pending", "in_progress", "completed"]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(**data)


class TaskManager:
    """Gestionnaire de tâches global."""

    _instance: "TaskManager | None" = None
    _tasks: list[Task] = []
    _next_id: int = 1

    def __new__(cls) -> "TaskManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tasks = []
            cls._instance._next_id = 1
        return cls._instance

    def add(self, content: str, status: str = "pending") -> Task:
        task = Task(
            id=self._next_id,
            content=content,
            status=status,  # type: ignore
        )
        self._tasks.append(task)
        self._next_id += 1
        return task

    def update(self, task_id: int, status: str) -> Task | None:
        for task in self._tasks:
            if task.id == task_id:
                task.status = status  # type: ignore
                return task
        return None

    def remove(self, task_id: int) -> bool:
        for i, task in enumerate(self._tasks):
            if task.id == task_id:
                self._tasks.pop(i)
                return True
        return False

    def get_all(self) -> list[Task]:
        return self._tasks.copy()

    def clear(self) -> None:
        self._tasks.clear()
        self._next_id = 1

    def to_markdown(self) -> str:
        """Exporte les tâches en Markdown."""
        lines = ["# 📋 Tâches THÉRÈSE", ""]

        pending = [t for t in self._tasks if t.status == "pending"]
        in_progress = [t for t in self._tasks if t.status == "in_progress"]
        completed = [t for t in self._tasks if t.status == "completed"]

        if in_progress:
            lines.append("## 🔄 En cours")
            for t in in_progress:
                lines.append(f"- [ ] **{t.content}** (#{t.id})")
            lines.append("")

        if pending:
            lines.append("## ⏳ À faire")
            for t in pending:
                lines.append(f"- [ ] {t.content} (#{t.id})")
            lines.append("")

        if completed:
            lines.append("## ✅ Terminé")
            for t in completed:
                lines.append(f"- [x] ~~{t.content}~~ (#{t.id})")
            lines.append("")

        if not self._tasks:
            lines.append("*Aucune tâche*")

        return "\n".join(lines)


# Instance globale
task_manager = TaskManager()


class TaskListTool(Tool):
    """Affiche la liste des tâches."""

    name = "task_list"
    description = (
        "Affiche la liste des tâches en cours, à faire et terminées. "
        "Utile pour suivre la progression du travail."
    )
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Filtrer par statut: pending, in_progress, completed, all",
                "enum": ["pending", "in_progress", "completed", "all"],
            },
        },
        "required": [],
    }

    async def execute(
        self,
        status: str = "all",
        **kwargs: Any,
    ) -> ToolResult:
        """Affiche les tâches."""
        tasks = task_manager.get_all()

        if status != "all":
            tasks = [t for t in tasks if t.status == status]

        if not tasks:
            return ToolResult(
                success=True,
                output="Aucune tâche" + (f" avec statut '{status}'" if status != "all" else ""),
            )

        return ToolResult(success=True, output=task_manager.to_markdown())


class TaskAddTool(Tool):
    """Ajoute une nouvelle tâche."""

    name = "task_add"
    description = (
        "Ajoute une ou plusieurs tâches à la liste. "
        "Utilisez pour planifier et suivre le travail."
    )
    parameters = {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress"],
                        },
                    },
                    "required": ["content"],
                },
                "description": "Liste des tâches à ajouter",
            },
        },
        "required": ["tasks"],
    }

    async def execute(
        self,
        tasks: list[dict],
        **kwargs: Any,
    ) -> ToolResult:
        """Ajoute des tâches."""
        added = []
        for task_data in tasks:
            task = task_manager.add(
                content=task_data["content"],
                status=task_data.get("status", "pending"),
            )
            added.append(task)

        output = f"✅ {len(added)} tâche(s) ajoutée(s):\n"
        for task in added:
            icon = "🔄" if task.status == "in_progress" else "⏳"
            output += f"  {icon} #{task.id}: {task.content}\n"

        return ToolResult(success=True, output=output)


class TaskUpdateTool(Tool):
    """Met à jour le statut d'une tâche."""

    name = "task_update"
    description = (
        "Met à jour le statut d'une tâche. "
        "Marquez les tâches comme en cours ou terminées."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "integer",
                "description": "ID de la tâche",
            },
            "status": {
                "type": "string",
                "description": "Nouveau statut",
                "enum": ["pending", "in_progress", "completed"],
            },
        },
        "required": ["task_id", "status"],
    }

    async def execute(
        self,
        task_id: int,
        status: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Met à jour une tâche."""
        task = task_manager.update(task_id, status)

        if not task:
            return ToolResult(
                success=False,
                output="",
                error=f"Tâche #{task_id} non trouvée",
            )

        icons = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}
        return ToolResult(
            success=True,
            output=f"{icons[status]} Tâche #{task_id} mise à jour: {task.content}",
        )
