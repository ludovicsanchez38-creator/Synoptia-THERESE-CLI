"""
Background Task Manager pour THERESE CLI.

Permet d'exécuter des commandes longues en arrière-plan
(npm install, tests, builds, etc.) sans bloquer l'UI.
"""

import asyncio
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable


class TaskStatus(Enum):
    """État d'une tâche."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """Une tâche en arrière-plan."""
    id: str
    command: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output: str = ""
    error: str = ""
    return_code: int | None = None
    process: subprocess.Popen | None = field(default=None, repr=False)

    def to_dict(self) -> dict:
        """Convertit en dict pour affichage."""
        return {
            "id": self.id,
            "command": self.command,
            "status": self.status.value,
            "created_at": self.created_at.strftime("%H:%M:%S"),
            "duration": self._get_duration(),
            "output_lines": len(self.output.split("\n")) if self.output else 0,
        }

    def _get_duration(self) -> str:
        """Calcule la durée de la tâche."""
        if self.started_at is None:
            return "n/a"

        end_time = self.completed_at or datetime.now()
        duration = (end_time - self.started_at).total_seconds()

        if duration < 60:
            return f"{int(duration)}s"
        elif duration < 3600:
            return f"{int(duration // 60)}m {int(duration % 60)}s"
        else:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            return f"{hours}h {minutes}m"


class BackgroundTaskManager:
    """
    Gestionnaire de tâches en arrière-plan.

    Usage:
    - /bg npm install : Lance npm install en background
    - /jobs : Liste les tâches
    - /kill <id> : Tue une tâche
    - /output <id> : Affiche l'output d'une tâche
    """

    MAX_TASKS = 10  # Limite de tâches simultanées
    MAX_OUTPUT_LINES = 100  # Lignes d'output gardées en mémoire

    def __init__(self):
        self._tasks: dict[str, BackgroundTask] = {}
        self._lock = asyncio.Lock()

    def _generate_id(self) -> str:
        """Génère un ID court unique."""
        return f"bg_{uuid.uuid4().hex[:6]}"

    async def run(
        self,
        command: str,
        working_dir: str | None = None,
        on_complete: Callable[[BackgroundTask], None] | None = None,
    ) -> tuple[bool, str]:
        """
        Lance une commande en arrière-plan.

        Args:
            command: Commande shell à exécuter
            working_dir: Répertoire de travail (optionnel)
            on_complete: Callback appelé quand la tâche termine

        Returns:
            (success, message) avec l'ID de la tâche si succès
        """
        async with self._lock:
            # Nettoyer les anciennes tâches terminées
            self._cleanup_old_tasks()

            # Vérifier la limite
            running = [t for t in self._tasks.values()
                      if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)]
            if len(running) >= self.MAX_TASKS:
                return False, f"Limite de {self.MAX_TASKS} tâches atteinte"

        task_id = self._generate_id()
        task = BackgroundTask(id=task_id, command=command)
        self._tasks[task_id] = task

        # Lancer dans un thread (non-bloquant)
        asyncio.create_task(self._execute_task(task, working_dir, on_complete))

        return True, f"Tâche lancée: `{task_id}` (`{command[:50]}...`)"

    async def _execute_task(
        self,
        task: BackgroundTask,
        working_dir: str | None,
        on_complete: Callable[[BackgroundTask], None] | None,
    ) -> None:
        """Exécute une tâche de manière asynchrone."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            process = await asyncio.create_subprocess_shell(
                task.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            # Lire l'output en streaming
            stdout, stderr = await process.communicate()

            task.output = stdout.decode("utf-8", errors="replace")
            task.error = stderr.decode("utf-8", errors="replace")
            task.return_code = process.returncode

            if task.return_code == 0:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.FAILED

        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

        finally:
            task.completed_at = datetime.now()
            if on_complete:
                on_complete(task)

    def kill(self, task_id: str) -> tuple[bool, str]:
        """
        Tue une tâche en cours.

        Returns:
            (success, message)
        """
        task = self._tasks.get(task_id)
        if not task:
            return False, f"Tâche `{task_id}` non trouvée"

        if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
            return False, f"Tâche `{task_id}` déjà terminée ({task.status.value})"

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()

        # Note: Le vrai kill du process nécessiterait de stocker le process
        # Pour l'instant on marque juste comme cancelled

        return True, f"Tâche `{task_id}` annulée"

    def get_task(self, task_id: str) -> BackgroundTask | None:
        """Récupère une tâche par son ID."""
        return self._tasks.get(task_id)

    def list_tasks(self, include_completed: bool = True) -> list[BackgroundTask]:
        """
        Liste les tâches.

        Args:
            include_completed: Inclure les tâches terminées

        Returns:
            Liste de tâches triées par date de création
        """
        tasks = list(self._tasks.values())

        if not include_completed:
            tasks = [t for t in tasks
                    if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)]

        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def get_output(self, task_id: str, tail: int = 50) -> str:
        """
        Récupère l'output d'une tâche.

        Args:
            task_id: ID de la tâche
            tail: Nombre de lignes à retourner (depuis la fin)

        Returns:
            Output de la tâche
        """
        task = self._tasks.get(task_id)
        if not task:
            return f"Tâche `{task_id}` non trouvée"

        lines = (task.output + task.error).strip().split("\n")
        if len(lines) > tail:
            lines = lines[-tail:]

        return "\n".join(lines) if lines else "(pas d'output)"

    def _cleanup_old_tasks(self) -> None:
        """Supprime les anciennes tâches terminées (garder les 20 dernières)."""
        completed = [
            t for t in self._tasks.values()
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]

        if len(completed) > 20:
            # Trier par date et supprimer les plus anciennes
            completed.sort(key=lambda t: t.completed_at or t.created_at)
            for task in completed[:-20]:
                del self._tasks[task.id]

    def to_markdown(self) -> str:
        """Formate les tâches en Markdown."""
        tasks = self.list_tasks()

        if not tasks:
            return """# Background Tasks

Aucune tâche en cours.

**Usage:**
- `/bg <command>` - Lancer une commande en background
- `/jobs` - Voir cette liste
- `/kill <id>` - Arrêter une tâche
- `/output <id>` - Voir l'output d'une tâche
"""

        status_icons = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "▶️",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "⛔",
        }

        lines = [
            "# Background Tasks",
            "",
            "| ID | Statut | Commande | Durée |",
            "|---|---|---|---|",
        ]

        for task in tasks[:10]:  # Max 10 dans le tableau
            icon = status_icons.get(task.status, "?")
            cmd = task.command[:30] + "..." if len(task.command) > 30 else task.command
            duration = task._get_duration()
            lines.append(f"| `{task.id}` | {icon} {task.status.value} | `{cmd}` | {duration} |")

        running = len([t for t in tasks if t.status == TaskStatus.RUNNING])
        if running > 0:
            lines.append("")
            lines.append(f"**{running} tâche(s) en cours**")

        lines.extend([
            "",
            "**Commands:** `/kill <id>` `/output <id>`",
        ])

        return "\n".join(lines)


# Instance globale (singleton)
_manager: BackgroundTaskManager | None = None


def get_background_manager() -> BackgroundTaskManager:
    """Récupère le gestionnaire de tâches background (singleton)."""
    global _manager
    if _manager is None:
        _manager = BackgroundTaskManager()
    return _manager
