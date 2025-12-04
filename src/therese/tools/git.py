"""Outils Git : gestion des dépôts et commits."""

import asyncio
import os
from pathlib import Path
from typing import Any

from .base import Tool, ToolResult


class GitTool(Tool):
    """Exécute des commandes Git."""

    name = "git"
    description = (
        "Exécute des commandes Git (status, diff, log, add, commit, branch, etc.). "
        "Sécurisé : bloque les commandes destructrices sans confirmation."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "La commande Git (sans 'git' devant). Ex: 'status', 'diff', 'log -5'",
            },
            "working_dir": {
                "type": "string",
                "description": "Répertoire de travail. Par défaut: répertoire courant",
            },
        },
        "required": ["command"],
    }

    # Commandes dangereuses qui nécessitent confirmation
    DANGEROUS_COMMANDS = [
        "push --force",
        "push -f",
        "reset --hard",
        "clean -fd",
        "checkout --force",
        "rebase",
        "merge --abort",
        "reset HEAD~",
    ]

    # Commandes interdites
    BLOCKED_COMMANDS = [
        "config user.email",
        "config user.name",
        "config --global",
    ]

    async def execute(
        self,
        command: str,
        working_dir: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Exécute une commande Git."""
        # Vérifications de sécurité
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Commande Git bloquée: {blocked}",
                )

        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in command:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Commande dangereuse détectée: {dangerous}. Utilisez bash directement si vous êtes sûr.",
                )

        try:
            cwd = working_dir or os.getcwd()

            # Vérifier que c'est un repo Git
            git_dir = Path(cwd) / ".git"
            if not git_dir.exists() and "init" not in command and "clone" not in command:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Pas un dépôt Git: {cwd}",
                )

            process = await asyncio.create_subprocess_shell(
                f"git {command}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60,
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            output = stdout_str
            if stderr_str and process.returncode != 0:
                output += f"\n[stderr]\n{stderr_str}" if output else stderr_str

            return ToolResult(
                success=process.returncode == 0,
                output=output or "(aucune sortie)",
                error=None if process.returncode == 0 else f"Code: {process.returncode}",
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error="Commande Git timeout après 60s",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur Git: {e}",
            )


class GitCommitTool(Tool):
    """Crée un commit Git structuré."""

    name = "git_commit"
    description = (
        "Crée un commit Git avec un message structuré. "
        "Analyse les changements et génère un message conventionnel."
    )
    parameters = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message de commit. Si vide, sera généré automatiquement.",
            },
            "type": {
                "type": "string",
                "description": "Type de commit: feat, fix, docs, style, refactor, test, chore",
                "enum": ["feat", "fix", "docs", "style", "refactor", "test", "chore"],
            },
            "scope": {
                "type": "string",
                "description": "Scope du commit (optionnel). Ex: auth, api, ui",
            },
            "add_all": {
                "type": "boolean",
                "description": "Ajouter tous les fichiers modifiés. Par défaut: false",
            },
        },
        "required": [],
    }

    async def execute(
        self,
        message: str | None = None,
        type: str = "feat",
        scope: str | None = None,
        add_all: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Crée un commit Git."""
        try:
            cwd = os.getcwd()

            # Add si demandé
            if add_all:
                process = await asyncio.create_subprocess_shell(
                    "git add -A",
                    cwd=cwd,
                )
                await process.wait()

            # Vérifier qu'il y a des changements
            process = await asyncio.create_subprocess_shell(
                "git diff --cached --stat",
                stdout=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, _ = await process.communicate()
            staged = stdout.decode().strip()

            if not staged:
                return ToolResult(
                    success=False,
                    output="",
                    error="Aucun changement à commiter. Utilisez add_all=true ou git add.",
                )

            # Construire le message
            if message:
                if scope:
                    full_message = f"{type}({scope}): {message}"
                else:
                    full_message = f"{type}: {message}"
            else:
                full_message = f"{type}: mise à jour"

            # Ajouter le footer THERESE
            full_message += "\n\n🤖 Généré avec THÉRÈSE CLI\n\nCo-Authored-By: THÉRÈSE <therese@synoptia.fr>"

            # Créer le commit
            process = await asyncio.create_subprocess_shell(
                f'git commit -m "{full_message}"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    output=output,
                    error="Échec du commit",
                )

            return ToolResult(
                success=True,
                output=f"Commit créé:\n{staged}\n\nMessage: {full_message.split(chr(10))[0]}",
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur: {e}",
            )


class GitStatusTool(Tool):
    """Affiche le statut Git de manière lisible."""

    name = "git_status"
    description = (
        "Affiche le statut Git du dépôt de manière claire et structurée. "
        "Montre les fichiers modifiés, ajoutés, supprimés et non suivis."
    )
    parameters = {
        "type": "object",
        "properties": {
            "working_dir": {
                "type": "string",
                "description": "Répertoire de travail",
            },
        },
        "required": [],
    }

    async def execute(
        self,
        working_dir: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Affiche le statut Git."""
        try:
            cwd = working_dir or os.getcwd()

            # Branche actuelle
            process = await asyncio.create_subprocess_shell(
                "git branch --show-current",
                stdout=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, _ = await process.communicate()
            branch = stdout.decode().strip() or "HEAD détachée"

            # Statut
            process = await asyncio.create_subprocess_shell(
                "git status --porcelain",
                stdout=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, _ = await process.communicate()
            status_lines = stdout.decode().strip().split("\n")

            # Parser les statuts
            staged = []
            modified = []
            untracked = []

            for line in status_lines:
                if not line:
                    continue
                status = line[:2]
                filename = line[3:]

                if status[0] in "MADRC":
                    staged.append((status[0], filename))
                if status[1] in "MD":
                    modified.append((status[1], filename))
                if status == "??":
                    untracked.append(filename)

            # Dernier commit
            process = await asyncio.create_subprocess_shell(
                "git log -1 --oneline",
                stdout=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, _ = await process.communicate()
            last_commit = stdout.decode().strip()

            # Formater la sortie
            output = [f"# Git Status - Branche: `{branch}`", ""]

            if last_commit:
                output.append(f"**Dernier commit:** {last_commit}")
                output.append("")

            if staged:
                output.append("## 📦 Staged (prêt à commiter)")
                for status, filename in staged:
                    icon = {"A": "🟢", "M": "🟡", "D": "🔴", "R": "🔄", "C": "📋"}.get(status, "❓")
                    output.append(f"  {icon} {filename}")
                output.append("")

            if modified:
                output.append("## 📝 Modifié (non staged)")
                for status, filename in modified:
                    icon = {"M": "🟡", "D": "🔴"}.get(status, "❓")
                    output.append(f"  {icon} {filename}")
                output.append("")

            if untracked:
                output.append("## ❓ Non suivi")
                for filename in untracked:
                    output.append(f"  📄 {filename}")
                output.append("")

            if not staged and not modified and not untracked:
                output.append("✅ Répertoire de travail propre")

            return ToolResult(success=True, output="\n".join(output))

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur: {e}",
            )
