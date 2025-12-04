"""
Application Textual principale pour THERESE CLI.

UI Terminal avec :
- THERESE en Bleu Blanc Rouge
- CLI en Orange Mistral
- Support des commandes slash
- Affichage des stats
"""

import asyncio
from pathlib import Path

from rich.console import RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Horizontal, Vertical
from textual.widgets import Footer, Input, Static

from ..agent import ThereseAgent
from ..commands import process_slash_command
from ..config import Colors, config
from .theme import THERESE_CSS


class Logo(Static):
    """Logo THERESE CLI avec couleurs françaises."""

    def render(self) -> RenderableType:
        """Render le logo avec les bonnes couleurs."""
        logo = Text()

        # THERESE en Bleu Blanc Rouge
        logo.append("T", style=f"bold {Colors.BLEU}")
        logo.append("H", style=f"bold {Colors.BLEU}")
        logo.append("É", style=f"bold {Colors.BLANC}")
        logo.append("R", style=f"bold {Colors.BLANC}")
        logo.append("È", style=f"bold {Colors.ROUGE}")
        logo.append("S", style=f"bold {Colors.ROUGE}")
        logo.append("E", style=f"bold {Colors.ROUGE}")

        logo.append(" ")

        # CLI en Orange Mistral
        logo.append("CLI", style=f"bold {Colors.ORANGE}")

        return logo


class StatusBar(Static):
    """Barre de statut avec infos modèle et tokens."""

    def __init__(self, agent: ThereseAgent, **kwargs) -> None:
        super().__init__(**kwargs)
        self.agent = agent

    def render(self) -> RenderableType:
        """Render la barre de statut."""
        stats = self.agent.get_stats()

        status = Text()
        status.append("📊 ", style="")
        status.append(f"{stats['model']}", style=f"bold {Colors.ORANGE}")
        status.append(" │ ", style="dim")
        status.append(f"Mode: {stats['mode']}", style=f"{Colors.BLEU}")
        status.append(" │ ", style="dim")
        status.append(f"Tokens: {stats['tokens']['total']:,}", style="dim")
        if stats['cost_usd'] > 0:
            status.append(f" (~${stats['cost_usd']:.4f})", style="dim")
        status.append(" │ ", style="dim")
        status.append(f"{stats['messages']} msgs", style="dim")

        return status

    def refresh_stats(self) -> None:
        """Rafraîchit les stats."""
        self.refresh()


class MessageWidget(Static):
    """Widget pour afficher un message."""

    def __init__(
        self,
        content: str,
        role: str = "assistant",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.content = content
        self.role = role

    def compose(self) -> ComposeResult:
        """Compose le message."""
        # Header
        if self.role == "user":
            header = Text("▶ Vous", style=f"bold {Colors.BLEU}")
        elif self.role == "assistant":
            header = Text("◀ THÉRÈSE", style=f"bold {Colors.ORANGE}")
        elif self.role == "command":
            header = Text("⌘ Commande", style=f"bold {Colors.SUCCESS}")
        else:
            header = Text("⚙ Outil", style=f"bold {Colors.SUCCESS}")

        yield Static(header, classes="message-header")

        # Contenu (Markdown)
        try:
            rendered = Markdown(self.content)
        except Exception:
            rendered = Text(self.content)

        yield Static(rendered, classes="message-content")

    def on_mount(self) -> None:
        """Style le message selon le rôle."""
        self.add_class(f"message-{self.role}")


class StreamingMessage(Static):
    """Widget pour un message en cours de streaming."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.chunks: list[str] = []

    def render(self) -> RenderableType:
        """Render le contenu actuel."""
        content = "".join(self.chunks)
        if not content:
            return Text("▌", style=f"blink {Colors.ORANGE}")

        try:
            return Markdown(content)
        except Exception:
            return Text(content)

    def append(self, chunk: str) -> None:
        """Ajoute un chunk au message."""
        self.chunks.append(chunk)
        self.refresh()

    def get_content(self) -> str:
        """Retourne le contenu complet."""
        return "".join(self.chunks)


class ThereseApp(App):
    """Application principale THERESE CLI."""

    CSS = THERESE_CSS

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quitter"),
        Binding("ctrl+l", "clear", "Effacer"),
        Binding("ctrl+r", "reset", "Reset"),
        Binding("escape", "cancel", "Annuler"),
        Binding("ctrl+t", "tree", "Tree"),
        Binding("ctrl+g", "git_status", "Git"),
    ]

    def __init__(self, working_dir: Path | None = None) -> None:
        super().__init__()
        if working_dir:
            config.working_dir = working_dir
        self.agent = ThereseAgent()
        self.is_processing = False
        self.status_bar: StatusBar | None = None

    def compose(self) -> ComposeResult:
        """Compose l'interface."""
        # Header avec logo
        with Horizontal(id="header"):
            yield Logo(id="logo")
            yield Static(
                Text.assemble(
                    ("  │  ", "dim"),
                    ("Mistral 3", f"{Colors.ORANGE_LIGHT}"),
                    (" 🇫🇷", ""),
                ),
                id="header-info",
            )

        # Zone de conversation
        yield ScrollableContainer(id="conversation")

        # Zone de saisie
        with Vertical(id="input-area"):
            yield Input(
                placeholder="Message ou /commande... (Tab pour complétion)",
                id="input",
            )

        # Status bar
        self.status_bar = StatusBar(self.agent, id="status")
        yield self.status_bar

        yield Footer()

    def on_mount(self) -> None:
        """Au montage de l'app."""
        # Focus sur l'input
        self.query_one("#input", Input).focus()

        # Message de bienvenue
        welcome = f"""Bienvenue dans **THÉRÈSE CLI** ! 🇫🇷

Je suis ton assistant de programmation propulsé par **Mistral 3**.

**Répertoire:** `{config.working_dir}`
**Modèle:** `{config.model}`
**Mode:** `{config.mode}`

**Commandes utiles:**
- `/help` - Voir toutes les commandes
- `/init` - Initialiser le projet
- `/tree` - Voir l'arborescence
- `/status` - Statut Git

**Raccourcis:** `Ctrl+L` effacer │ `Ctrl+R` reset │ `Ctrl+T` tree │ `Ctrl+G` git

Que puis-je faire pour toi ?"""

        self._add_message(welcome, "assistant")

    def _add_message(self, content: str, role: str) -> None:
        """Ajoute un message à la conversation."""
        conversation = self.query_one("#conversation", ScrollableContainer)
        message = MessageWidget(content, role, classes="message")
        conversation.mount(message)
        message.scroll_visible()

    def _add_streaming_message(self) -> StreamingMessage:
        """Ajoute un message en streaming."""
        conversation = self.query_one("#conversation", ScrollableContainer)
        message = StreamingMessage(classes="message message-assistant")
        conversation.mount(message)
        return message

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Quand l'utilisateur soumet un message."""
        if self.is_processing:
            return

        user_input = event.value.strip()
        if not user_input:
            return

        # Effacer l'input
        event.input.value = ""

        # Vérifier si c'est une commande slash
        if user_input.startswith("/"):
            is_command, response = await process_slash_command(user_input)
            if is_command:
                # Gérer les commandes spéciales
                if response == "__CLEAR__":
                    self.action_clear()
                    return
                elif response == "__RESET__":
                    self.action_reset()
                    return
                elif response == "__COMPACT__":
                    result = self.agent.compact()
                    self._add_message(result, "command")
                    return

                self._add_message(user_input, "user")
                self._add_message(response, "command")
                return

        # Ajouter le message utilisateur
        self._add_message(user_input, "user")

        # Traiter la requête
        await self._process_request(user_input)

    @work(exclusive=True)
    async def _process_request(self, user_input: str) -> None:
        """Traite une requête utilisateur."""
        self.is_processing = True

        # Créer le message streaming
        streaming_msg = self._add_streaming_message()

        try:
            async for chunk in self.agent.chat(user_input):
                streaming_msg.append(chunk)
                # Scroll vers le bas
                streaming_msg.scroll_visible()
                # Petit délai pour l'animation
                await asyncio.sleep(0.01)

            # Mettre à jour la barre de statut
            if self.status_bar:
                self.status_bar.refresh_stats()

        except Exception as e:
            streaming_msg.append(f"\n\n**Erreur:** {e}")

        finally:
            self.is_processing = False
            # Focus retour sur l'input
            self.query_one("#input", Input).focus()

    def action_clear(self) -> None:
        """Efface la conversation (garde l'historique agent)."""
        conversation = self.query_one("#conversation", ScrollableContainer)
        conversation.remove_children()

    def action_reset(self) -> None:
        """Réinitialise complètement la conversation."""
        self.agent.reset()
        self.action_clear()
        self._add_message("Conversation réinitialisée. Comment puis-je t'aider ?", "assistant")
        if self.status_bar:
            self.status_bar.refresh_stats()

    def action_cancel(self) -> None:
        """Annule l'opération en cours."""
        if self.is_processing:
            self.notify("Annulation en cours...")

    async def action_tree(self) -> None:
        """Affiche l'arborescence."""
        _, response = await process_slash_command("/tree")
        self._add_message(response, "command")

    async def action_git_status(self) -> None:
        """Affiche le statut Git."""
        _, response = await process_slash_command("/status")
        self._add_message(response, "command")
