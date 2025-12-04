"""Outil d'exécution de commandes bash."""

import asyncio
import os
from typing import Any

from .base import Tool, ToolResult


class BashTool(Tool):
    """Exécute des commandes bash."""

    name = "bash"
    description = (
        "Exécute une commande bash dans le terminal. "
        "Utilisez pour git, npm, python, et autres commandes système. "
        "Timeout par défaut: 120 secondes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "La commande bash à exécuter",
            },
            "working_dir": {
                "type": "string",
                "description": "Répertoire de travail (optionnel)",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout en secondes. Par défaut: 120",
            },
        },
        "required": ["command"],
    }

    # Commandes dangereuses interdites
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "rm -rf ~",
        "> /dev/sda",
        "mkfs.",
        ":(){:|:&};:",  # Fork bomb
    ]

    async def execute(
        self,
        command: str,
        working_dir: str | None = None,
        timeout: int = 120,
        **kwargs: Any,
    ) -> ToolResult:
        """Exécute la commande bash."""
        # Vérification de sécurité basique
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Commande bloquée pour raison de sécurité: {blocked}",
                )

        try:
            # Configurer l'environnement
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"

            # Répertoire de travail
            cwd = working_dir or os.getcwd()

            # Créer le processus
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Commande timeout après {timeout}s: {command}",
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Tronquer si trop long
            max_output = 30000
            if len(stdout_str) > max_output:
                stdout_str = stdout_str[:max_output] + "\n... [sortie tronquée]"
            if len(stderr_str) > max_output:
                stderr_str = stderr_str[:max_output] + "\n... [erreur tronquée]"

            output = ""
            if stdout_str:
                output += stdout_str
            if stderr_str:
                output += f"\n[stderr]\n{stderr_str}" if output else stderr_str

            success = process.returncode == 0

            return ToolResult(
                success=success,
                output=output or "(aucune sortie)",
                error=None if success else f"Code de sortie: {process.returncode}",
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur d'exécution: {e}",
            )
