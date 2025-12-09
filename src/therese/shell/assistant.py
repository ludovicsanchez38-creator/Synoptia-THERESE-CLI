"""
Shell Assistant - Analyse et corrige les erreurs de commandes.

Inspiré de shai (OVH) qui propose des corrections automatiques
quand une commande échoue dans le terminal.
"""

import os
import sys
from dataclasses import dataclass
from typing import Iterator

from rich.console import Console
from rich.text import Text

from ..config import Colors

console = Console(stderr=True)


@dataclass
class CommandError:
    """Représente une erreur de commande shell."""

    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    cwd: str = ""

    @property
    def output(self) -> str:
        """Combine stdout et stderr."""
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)

    def truncated_output(self, max_chars: int = 3000) -> str:
        """Retourne l'output tronqué si nécessaire."""
        output = self.output
        if len(output) > max_chars:
            return output[:max_chars] + f"\n... ({len(output) - max_chars} caractères tronqués)"
        return output


class ShellAssistant:
    """
    Assistant shell qui analyse les erreurs et propose des corrections.

    Utilise Mistral pour comprendre l'erreur et suggérer une commande
    corrigée ou une solution.
    """

    # Codes d'erreur courants avec contexte
    ERROR_CONTEXTS = {
        1: "Erreur générale",
        2: "Mauvaise utilisation de commande shell",
        126: "Commande non exécutable (permissions)",
        127: "Commande non trouvée",
        128: "Argument invalide à exit",
        130: "Terminé par Ctrl+C",
        137: "Processus tué (SIGKILL)",
        139: "Segmentation fault",
        143: "Terminé par SIGTERM",
        255: "Code de sortie hors limites",
    }

    def __init__(self):
        self._agent = None

    @property
    def agent(self):
        """Lazy loading de l'agent pour éviter import circulaire."""
        if self._agent is None:
            from ..agent import ThereseAgent
            self._agent = ThereseAgent()
        return self._agent

    def analyze_error(self, error: CommandError) -> Iterator[str]:
        """
        Analyse une erreur de commande et propose une correction.

        Yields des chunks de texte pour le streaming.
        """
        # Construire le prompt d'analyse
        error_context = self.ERROR_CONTEXTS.get(error.exit_code, "Erreur inconnue")

        prompt = f"""Tu es un expert shell/terminal. Une commande a échoué.

**Commande:** `{error.command}`
**Code de sortie:** {error.exit_code} ({error_context})
**Répertoire:** {error.cwd or 'inconnu'}

**Output/Erreur:**
```
{error.truncated_output()}
```

**Ta mission:**
1. Identifie la cause de l'erreur
2. Propose UNE commande corrigée

**Format de réponse:**
- Ligne 1: Explication courte (1 phrase)
- Ligne 2: Commande corrigée (sans bloc de code, juste la commande)

Exemple de réponse:
Le package n'existe pas, essayez avec le bon nom.
npm install express
"""

        # Streamer la réponse
        for chunk in self.agent.chat_sync(prompt):
            yield chunk

    def quick_fix(self, error: CommandError) -> str:
        """
        Retourne uniquement la commande corrigée (pas d'explication).

        Utilisé pour le mode non-interactif où on veut juste le fix.
        """
        prompt = f"""Commande échouée (code {error.exit_code}):
```
{error.command}
```

Erreur:
```
{error.truncated_output(1500)}
```

Réponds UNIQUEMENT avec la commande corrigée. Rien d'autre."""

        response = "".join(self.agent.chat_sync(prompt))

        # Nettoyer la réponse (retirer backticks si présents)
        fix = response.strip()
        if fix.startswith("```"):
            lines = fix.split("\n")
            fix = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        if fix.startswith("`") and fix.endswith("`"):
            fix = fix[1:-1]

        return fix.strip()

    def suggest_fix_interactive(self, error: CommandError) -> str | None:
        """
        Mode interactif : affiche l'analyse et demande confirmation.

        Returns:
            La commande à exécuter, ou None si l'utilisateur refuse.
        """
        console.print()
        console.print(
            Text.assemble(
                ("💡 ", ""),
                ("THÉRÈSE", f"bold {Colors.ORANGE}"),
                (" détecte une erreur ", ""),
                (f"(code {error.exit_code})", "dim"),
            )
        )
        console.print()

        # Streamer l'analyse
        console.print(f"[bold {Colors.BLEU}]Analyse:[/]", end=" ")
        full_response = []
        for chunk in self.analyze_error(error):
            console.print(chunk, end="")
            full_response.append(chunk)
        console.print("\n")

        # Extraire la commande suggérée (dernière ligne non vide)
        response_text = "".join(full_response)
        lines = [l.strip() for l in response_text.strip().split("\n") if l.strip()]

        if not lines:
            console.print("[yellow]Pas de suggestion trouvée[/]")
            return None

        # La commande est généralement la dernière ligne
        suggested_command = lines[-1]

        # Nettoyer si entourée de backticks
        if suggested_command.startswith("`") and suggested_command.endswith("`"):
            suggested_command = suggested_command[1:-1]

        # Demander confirmation
        console.print(f"[bold]Commande suggérée:[/]")
        console.print(f"  [green]{suggested_command}[/]")
        console.print()

        try:
            response = console.input("[dim]Exécuter ? [o/N/e(dit)]:[/] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Annulé[/]")
            return None

        if response in ("o", "oui", "y", "yes"):
            return suggested_command
        elif response in ("e", "edit", "m", "modifier"):
            try:
                edited = console.input("[dim]Modifier la commande:[/] ").strip()
                return edited if edited else None
            except (KeyboardInterrupt, EOFError):
                return None
        else:
            console.print("[dim]Annulé[/]")
            return None


# Instance globale
shell_assistant = ShellAssistant()
