"""
Application Textual principale pour THERESE CLI.

UI Terminal avec :
- THERESE en Bleu Blanc Rouge
- CLI en Orange Mistral
- Support des commandes slash
- Affichage des stats
- Streaming Markdown optimisé (Textual 6.0+)
- Support drag & drop fichiers et images
"""

import asyncio
import os
import random
import re
from pathlib import Path

from rich.console import RenderableType
from rich.markdown import Markdown as RichMarkdown
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Input, Static, Markdown, TextArea, ListView, ListItem, Label

# Extensions d'images supportées
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

# Messages de réflexion humoristiques français
THINKING_MESSAGES = [
    "🥖 Fait cuire une baguette...",
    "🧀 Affine le camembert...",
    "🍷 Décante le Bordeaux...",
    "🥐 Prépare les croissants...",
    "🐓 Consulte le coq gaulois...",
    "🗼 Escalade la Tour Eiffel...",
    "🎨 Retouche la Joconde...",
    "🐌 Cuisine les escargots...",
    "🧄 Épluche l'ail de René...",
    "🥩 Prépare le saucisson...",
    "☕ Sert le petit café...",
    "🎭 Répète du Molière...",
    "🚴 Pédale sur le Tour...",
    "🏰 Visite Versailles...",
    "📜 Lit la Déclaration des Droits...",
    "⚔️ Aiguise Excalibur...",
    "🎺 Joue la Marseillaise...",
    "🧅 Pleure sur les oignons...",
    "🦪 Ouvre les huîtres...",
    "🍾 Sabrer le champagne...",
    "🐸 Discute avec les grenouilles...",
    "🌻 Cueille des tournesols...",
    "🎩 Ajuste le béret...",
    "📯 Sonne le clairon...",
    "🏋️ Porte le sac de René...",
]

from textual.message import Message

from ..agent import ThereseAgent
from ..commands import process_slash_command
from ..config import Colors, config
from .theme import THERESE_CSS


def clean_path(path: str) -> str:
    """
    Nettoie un chemin collé depuis Finder/terminal.

    Gère :
    - Quotes simples/doubles : '/path/to/file' -> /path/to/file
    - Espaces échappés : /path/to/My\\ File -> /path/to/My File
    - Espaces en début/fin
    """
    # Retirer les quotes
    path = path.strip()
    if (path.startswith("'") and path.endswith("'")) or \
       (path.startswith('"') and path.endswith('"')):
        path = path[1:-1]

    # Retirer les backslashes d'échappement (espaces)
    path = path.replace("\\ ", " ")
    path = path.replace("\\", "")  # Autres échappements

    return path.strip()


def extract_paths_from_text(text: str) -> tuple[list[str], list[str], str]:
    """
    Extrait les chemins de fichiers et images d'un texte.

    Détecte les chemins qui commencent par /, ~, ou ./
    Gère les chemins avec espaces (quand collés depuis Finder)
    Fonctionne même si le chemin est dans du texte.

    Returns:
        (file_paths, image_paths, cleaned_text)
    """
    file_paths = []
    image_paths = []
    cleaned_text = text

    # Pattern pour trouver les chemins potentiels dans le texte
    # Cherche : /chemin/... ou ~/chemin/... ou ./chemin/...
    # Avec support des espaces échappés (\ )

    # D'abord, essayer de trouver des chemins avec backslash (échappés)
    # Format Finder : /path/to/My\ Folder/file.txt
    import re

    # Pattern pour chemins avec espaces échappés
    escaped_pattern = r'(/(?:[^\s]|\\ )+)'
    # Pattern pour chemins entre quotes
    quoted_pattern = r'["\'](/[^"\']+)["\']'
    # Pattern pour chemins simples (sans espaces)
    simple_pattern = r'(?:^|\s)((?:/|~/|\./)[\w\-./]+)'

    found_paths = []

    # Chercher les chemins entre quotes d'abord
    for match in re.finditer(quoted_pattern, text):
        path = match.group(1)
        found_paths.append((match.start(), match.end(), path))

    # Chercher les chemins avec espaces échappés
    for match in re.finditer(escaped_pattern, text):
        path = match.group(1)
        if '\\' in path:  # Contient des échappements
            found_paths.append((match.start(), match.end(), path))

    # Chercher les chemins simples
    for match in re.finditer(simple_pattern, text):
        path = match.group(1)
        # Éviter les doublons
        if not any(p[2] == path for p in found_paths):
            found_paths.append((match.start(), match.end(), path))

    # Trier par position (du dernier au premier pour faciliter le remplacement)
    found_paths.sort(key=lambda x: x[0], reverse=True)

    for start, end, raw_path in found_paths:
        # Nettoyer le chemin
        cleaned_path = clean_path(raw_path)
        expanded = os.path.expanduser(cleaned_path)

        if os.path.exists(expanded):
            ext = Path(expanded).suffix.lower()
            if ext in IMAGE_EXTENSIONS:
                if expanded not in image_paths:
                    image_paths.append(expanded)
            else:
                if expanded not in file_paths:
                    file_paths.append(expanded)
            # Retirer le chemin du texte
            # Trouver le vrai début/fin dans cleaned_text
            cleaned_text = cleaned_text.replace(raw_path, '').strip()

    # Nettoyer les espaces multiples
    cleaned_text = ' '.join(cleaned_text.split())

    return file_paths, image_paths, cleaned_text


class ExpandableInput(TextArea):
    """Zone de saisie qui s'agrandit avec le contenu (3-10 lignes) + historique."""

    DEFAULT_CSS = """
    ExpandableInput {
        height: auto;
        min-height: 3;
        max-height: 10;
        background: #0D1117;
        border: solid #30363D;
        padding: 0 1;
    }

    ExpandableInput:focus {
        border: solid #FF7000;
    }
    """

    # Historique partagé entre toutes les instances
    _history: list[str] = []
    _max_history: int = 100

    class Submitted(Message):
        """Message émis lors de la soumission avec chemins détectés."""

        def __init__(
            self,
            input_widget: "ExpandableInput",
            value: str,
            file_paths: list[str] | None = None,
            image_paths: list[str] | None = None,
        ) -> None:
            super().__init__()
            self.input = input_widget
            self.value = value
            self.file_paths = file_paths or []
            self.image_paths = image_paths or []

    def __init__(self, placeholder: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._placeholder = placeholder
        self.show_line_numbers = False
        self._history_index = -1  # -1 = pas en mode historique
        self._current_input = ""  # Sauvegarde du texte en cours

    def on_mount(self) -> None:
        """Configure le TextArea."""
        # Afficher le placeholder si vide
        if not self.text:
            self.placeholder = self._placeholder

    def _add_to_history(self, text: str) -> None:
        """Ajoute un texte à l'historique."""
        if text and (not self._history or self._history[-1] != text):
            self._history.append(text)
            if len(self._history) > self._max_history:
                self._history.pop(0)

    def _navigate_history(self, direction: int) -> None:
        """Navigue dans l'historique (-1 = plus ancien, +1 = plus récent)."""
        if not self._history:
            return

        # Sauvegarder le texte actuel si on commence à naviguer
        if self._history_index == -1:
            self._current_input = self.text

        new_index = self._history_index + direction

        if new_index < -1:
            new_index = -1
        elif new_index >= len(self._history):
            new_index = len(self._history) - 1

        self._history_index = new_index

        if self._history_index == -1:
            # Retour au texte actuel
            self.text = self._current_input
        else:
            # Afficher l'élément de l'historique (du plus récent au plus ancien)
            history_pos = len(self._history) - 1 - self._history_index
            if 0 <= history_pos < len(self._history):
                self.text = self._history[history_pos]

    def on_paste(self, event) -> None:
        """Intercepte le paste pour détecter les fichiers droppés/collés."""
        text = event.text if hasattr(event, 'text') else ""

        if not text:
            return

        # Nettoyer le texte (retirer quotes et backslashes d'échappement)
        cleaned = clean_path(text.strip())
        expanded = os.path.expanduser(cleaned)

        # Vérifier si c'est un chemin existant (fichier ou dossier)
        if os.path.exists(expanded):
            event.prevent_default()
            event.stop()

            ext = Path(expanded).suffix.lower()
            if ext in IMAGE_EXTENSIONS:
                # Image - émettre un message pour envoi direct
                self.post_message(self.Submitted(self, "Analyse cette image.", [], [expanded]))
            else:
                # Fichier/dossier - insérer le chemin dans l'input
                self.insert(expanded)
        # Sinon laisser le paste normal (pas de notification)

    async def _on_key(self, event) -> None:
        """Gère Enter, flèches haut/bas pour l'historique."""
        # Flèche haut = historique précédent
        if event.key == "up":
            # Seulement si on est sur la première ligne
            if self.cursor_location[0] == 0:
                event.prevent_default()
                event.stop()
                self._navigate_history(1)  # Plus ancien
                return

        # Flèche bas = historique suivant
        if event.key == "down":
            # Seulement si on est sur la dernière ligne
            lines = self.text.split('\n')
            if self.cursor_location[0] == len(lines) - 1:
                event.prevent_default()
                event.stop()
                self._navigate_history(-1)  # Plus récent
                return

        # Ctrl+J = nouvelle ligne (alternative à Shift+Enter qui ne marche pas partout)
        if event.key == "ctrl+j":
            event.prevent_default()
            event.stop()
            self.insert("\n")
            return

        # Enter = soumettre
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            raw_text = self.text.strip()
            if raw_text:
                # Ajouter à l'historique
                self._add_to_history(raw_text)
                self._history_index = -1  # Reset navigation

                # Extraire les chemins du texte
                file_paths, image_paths, cleaned_text = extract_paths_from_text(raw_text)
                self.post_message(self.Submitted(
                    self,
                    cleaned_text or raw_text,
                    file_paths,
                    image_paths,
                ))
                self.text = ""
        # Note: Shift+Enter ne fonctionne pas dans tous les terminaux


class BigLogo(Static):
    """Grand logo THERESE CLI avec ASCII art coloré."""

    def render(self) -> RenderableType:
        """Render le grand logo ASCII avec TH bleu, ERE blanc, SE rouge, CLI orange."""
        # Chaque lettre en ASCII art (8 caractères de large chacune)
        # T = 8 chars, H = 9 chars, E = 8 chars, R = 8 chars, E = 8 chars, S = 8 chars, E = 8 chars

        # TH (bleu) - colonnes 0-17
        th = [
            "████████╗██╗  ██╗",
            "╚══██╔══╝██║  ██║",
            "   ██║   ███████║",
            "   ██║   ██╔══██║",
            "   ██║   ██║  ██║",
            "   ╚═╝   ╚═╝  ╚═╝",
        ]

        # ERE (blanc) - colonnes 18-41
        ere = [
            "███████╗██████╗ ███████╗",
            "██╔════╝██╔══██╗██╔════╝",
            "█████╗  ██████╔╝█████╗  ",
            "██╔══╝  ██╔══██╗██╔══╝  ",
            "███████╗██║  ██║███████╗",
            "╚══════╝╚═╝  ╚═╝╚══════╝",
        ]

        # SE (rouge) - colonnes 42-57
        se = [
            "███████╗███████╗",
            "██╔════╝██╔════╝",
            "███████╗█████╗  ",
            "╚════██║██╔══╝  ",
            "███████║███████╗",
            "╚══════╝╚══════╝",
        ]

        # CLI (orange)
        cli = [
            "   ██████╗██╗     ██╗",
            "  ██╔════╝██║     ██║",
            "  ██║     ██║     ██║",
            "  ██║     ██║     ██║",
            "  ╚██████╗███████╗██║",
            "   ╚═════╝╚══════╝╚═╝",
        ]

        logo = Text()
        logo.append("\n")

        for i in range(6):
            logo.append(th[i], style=f"bold {Colors.BLEU}")
            logo.append(ere[i], style=f"bold {Colors.BLANC}")
            logo.append(se[i], style=f"bold {Colors.ROUGE}")
            logo.append(cli[i], style=f"bold {Colors.ORANGE}")
            logo.append("\n")

        # Sous-titre
        logo.append("\n")
        logo.append("        🇫🇷 Assistant de code IA français", style=f"italic {Colors.TEXT_DIM}")
        logo.append("  •  ", style="dim")
        logo.append("Propulsé par Mistral 3", style=f"italic {Colors.ORANGE}")
        logo.append("  🔥\n\n", style="")
        logo.append("                              Créé par ", style=f"dim")
        logo.append("Synoptia", style=f"bold {Colors.BLEU}")
        logo.append(" ✨\n", style="")

        return logo


class Logo(Static):
    """Petit logo pour le header."""

    def render(self) -> RenderableType:
        """Render le logo compact."""
        logo = Text()
        logo.append("THÉRÈSE", style=f"bold {Colors.BLEU}")
        logo.append(" CLI", style=f"bold {Colors.ORANGE}")
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

        # Contenu (Markdown) - utilise RichMarkdown pour le rendu dans Static
        try:
            rendered = RichMarkdown(self.content)
        except Exception:
            rendered = Text(self.content)

        yield Static(rendered, classes="message-content")

    def on_mount(self) -> None:
        """Style le message selon le rôle."""
        self.add_class(f"message-{self.role}")


class StreamingMessage(Vertical):
    """Widget pour un message en cours de streaming avec Markdown optimisé."""

    DEFAULT_CSS = """
    StreamingMessage {
        height: auto;
        min-height: 5;
        padding: 1 2;
        background: #161B22;
        border: solid #FF7000;
        margin: 1 0;
    }

    StreamingMessage .streaming-header {
        margin-bottom: 1;
    }

    StreamingMessage .streaming-thinking {
        min-height: 2;
    }

    StreamingMessage .streaming-status {
        color: #7D8590;
        margin-top: 1;
    }

    StreamingMessage Markdown {
        margin: 0;
        padding: 0;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.thinking_message = random.choice(THINKING_MESSAGES)
        self.thinking_timer = None
        self._stream = None
        self._content_started = False
        self._markdown_widget: Markdown | None = None
        self._thinking_widget: Static | None = None
        self._status_widget: Static | None = None
        self._cot_widget: Static | None = None  # Widget pour afficher le COT
        self._chunks: list[str] = []
        self._pending_chunks: list[str] = []  # Buffer pour batching
        self._last_flush = 0.0  # Timestamp du dernier flush
        self._start_time = 0.0  # Pour calculer le temps écoulé
        self._char_count = 0  # Compteur de caractères (proxy pour tokens)
        self._current_tool: str | None = None  # Outil en cours
        self._cot_chunks: list[str] = []  # Chain of Thought (raisonnement caché)
        self._cot_visible = False  # Toggle pour afficher/cacher le COT
        self._is_thinking = False  # True pendant la phase de réflexion Magistral

    def compose(self) -> ComposeResult:
        """Compose le widget avec header et zone markdown."""
        import time
        self._start_time = time.time()

        # Header THÉRÈSE
        header = Text()
        header.append("◀ THÉRÈSE", style=f"bold {Colors.ORANGE}")
        yield Static(header, classes="streaming-header")

        # Message de réflexion (visible au début)
        thinking = Text()
        thinking.append(self.thinking_message, style=f"italic {Colors.ORANGE}")
        self._thinking_widget = Static(thinking, classes="streaming-thinking")
        yield self._thinking_widget

        # Widget pour le Chain of Thought (caché par défaut)
        self._cot_widget = Static("", classes="streaming-cot")
        self._cot_widget.display = False
        yield self._cot_widget

        # Widget Markdown pour le contenu streamé (caché au début)
        self._markdown_widget = Markdown("", classes="streaming-content")
        self._markdown_widget.display = False
        yield self._markdown_widget

        # Barre de statut en bas
        self._status_widget = Static("", classes="streaming-status")
        yield self._status_widget

    def on_mount(self) -> None:
        """Initialise les timers."""
        self.thinking_timer = self.set_interval(1.0, self._update_status)

    def on_unmount(self) -> None:
        """Nettoie le timer proprement."""
        if self.thinking_timer:
            self.thinking_timer.stop()
            self.thinking_timer = None

    def _update_status(self) -> None:
        """Met à jour la barre de statut."""
        import time

        elapsed = int(time.time() - self._start_time)
        tokens_approx = self._char_count // 4  # ~4 chars par token

        status = Text()

        if not self._content_started:
            # Phase réflexion - changer le message
            self.thinking_message = random.choice(THINKING_MESSAGES)
            if self._thinking_widget:
                thinking = Text()
                thinking.append(self.thinking_message, style=f"italic {Colors.ORANGE}")
                self._thinking_widget.update(thinking)
            status.append(f"réfléchit... ", style="dim")
        elif self._current_tool:
            # Outil en cours
            status.append(f"⚙ {self._current_tool} ", style=f"{Colors.SUCCESS}")
        else:
            # Streaming
            status.append("● streaming ", style=f"{Colors.ORANGE}")

        status.append(f"(esc annuler · {elapsed}s", style="dim")
        if tokens_approx > 0:
            status.append(f" · ↓{tokens_approx} tokens", style="dim")
        status.append(")", style="dim")

        if self._status_widget:
            self._status_widget.update(status)

    def set_tool(self, tool_name: str | None) -> None:
        """Définit l'outil en cours d'exécution."""
        self._current_tool = tool_name
        self._update_status()

    async def start_stream(self) -> None:
        """Initialise le MarkdownStream pour streaming efficace."""
        if self._markdown_widget:
            self._stream = Markdown.get_stream(self._markdown_widget)

    def start_stream_sync(self) -> None:
        """Version synchrone de start_stream (pour call_from_thread)."""
        if self._markdown_widget:
            self._stream = Markdown.get_stream(self._markdown_widget)

    async def append(self, chunk: str) -> None:
        """Ajoute un chunk au message avec batching pour performance."""
        import time

        # Détecter les chunks de raisonnement (COT) de Magistral
        if chunk.startswith("__THINK__"):
            # Stocker le COT mais ne pas l'afficher
            cot_text = chunk[9:]  # Retirer le préfixe __THINK__
            self._cot_chunks.append(cot_text)
            self._is_thinking = True
            self._char_count += len(cot_text)
            # Les messages 🥖🧀 restent visibles pendant le thinking
            return

        # Si on sort du mode thinking, transition vers le contenu
        if self._is_thinking and not chunk.startswith("__THINK__"):
            self._is_thinking = False

        # Accumuler les chunks de contenu
        self._chunks.append(chunk)
        self._pending_chunks.append(chunk)
        self._char_count += len(chunk)

        # Premier chunk de contenu: transition du thinking au contenu
        if not self._content_started:
            self._content_started = True
            self._last_flush = time.time()

            # Arrêter le timer des messages humoristiques
            if self.thinking_timer:
                self.thinking_timer.stop()
                self.thinking_timer = None

            # Cacher le thinking, montrer le markdown
            if self._thinking_widget:
                self._thinking_widget.display = False
            if self._markdown_widget:
                self._markdown_widget.display = True

            # Initialiser le stream si pas fait
            if not self._stream and self._markdown_widget:
                self._stream = Markdown.get_stream(self._markdown_widget)

        # Batching: flush tous les 50ms ou si buffer > 100 chars
        now = time.time()
        pending_size = sum(len(c) for c in self._pending_chunks)

        if (now - self._last_flush >= 0.05) or (pending_size >= 100):
            if self._stream and self._pending_chunks:
                batch = "".join(self._pending_chunks)
                await self._stream.write(batch)
                self._pending_chunks.clear()
                self._last_flush = now

    def append_sync(self, chunk: str) -> None:
        """Version synchrone de append (pour call_from_thread) avec buffering."""
        import time

        # Détecter les chunks de raisonnement (COT) de Magistral
        if chunk.startswith("__THINK__"):
            cot_text = chunk[9:]
            self._cot_chunks.append(cot_text)
            self._is_thinking = True
            self._char_count += len(cot_text)
            return

        if self._is_thinking and not chunk.startswith("__THINK__"):
            self._is_thinking = False

        self._chunks.append(chunk)
        self._pending_chunks.append(chunk)
        self._char_count += len(chunk)

        # Premier chunk: transition du thinking au contenu
        if not self._content_started:
            self._content_started = True
            self._last_flush = time.time()
            if self.thinking_timer:
                self.thinking_timer.stop()
                self.thinking_timer = None
            if self._thinking_widget:
                self._thinking_widget.display = False
            if self._markdown_widget:
                self._markdown_widget.display = True

        # BUFFERING: Update seulement toutes les 200ms ou tous les 500 chars
        # Évite O(n²) sur les longs outputs
        now = time.time()
        pending_size = sum(len(c) for c in self._pending_chunks)

        if (now - self._last_flush) >= 0.2 or pending_size >= 500:
            if self._markdown_widget:
                full_content = "".join(self._chunks)
                self._markdown_widget.update(full_content)
            self._pending_chunks.clear()
            self._last_flush = now

    def stop_stream_sync(self) -> None:
        """Version synchrone de stop_stream (pour call_from_thread)."""
        import time

        if self.thinking_timer:
            self.thinking_timer.stop()
            self.thinking_timer = None

        # FLUSH: S'assurer que tous les chunks pending sont affichés avant "terminé"
        if self._pending_chunks and self._markdown_widget:
            full_content = "".join(self._chunks)
            self._markdown_widget.update(full_content)
            self._pending_chunks.clear()

        # Afficher statut final
        if self._status_widget:
            elapsed = int(time.time() - self._start_time)
            tokens_approx = self._char_count // 4
            final_status = Text()
            final_status.append("✓ terminé", style=f"{Colors.SUCCESS}")
            final_status.append(f" ({elapsed}s · {tokens_approx} tokens)", style="dim")
            if self._cot_chunks:
                cot_tokens = sum(len(c) for c in self._cot_chunks) // 4
                final_status.append(f" · 🧠 {cot_tokens} tokens thinking ", style="dim")
                final_status.append("[Ctrl+O voir]", style=f"{Colors.BLEU}")
            self._status_widget.update(final_status)

    async def stop_stream(self) -> None:
        """Arrête proprement le stream."""
        # Arrêter le timer de statut
        if self.thinking_timer:
            self.thinking_timer.stop()
            self.thinking_timer = None

        # Flush les chunks restants
        if self._stream and self._pending_chunks:
            batch = "".join(self._pending_chunks)
            await self._stream.write(batch)
            self._pending_chunks.clear()

        if self._stream:
            await self._stream.stop()
            self._stream = None

        # Afficher statut final
        if self._status_widget:
            import time
            elapsed = int(time.time() - self._start_time)
            tokens_approx = self._char_count // 4
            final_status = Text()
            final_status.append("✓ terminé", style=f"{Colors.SUCCESS}")
            final_status.append(f" ({elapsed}s · {tokens_approx} tokens)", style="dim")
            # Si on a du COT, indiquer qu'on peut l'afficher
            if self._cot_chunks:
                cot_tokens = sum(len(c) for c in self._cot_chunks) // 4
                final_status.append(f" · 🧠 {cot_tokens} tokens thinking ", style="dim")
                final_status.append("[Ctrl+O voir]", style=f"{Colors.BLEU}")
            self._status_widget.update(final_status)

    def toggle_cot(self) -> None:
        """Affiche/cache le Chain of Thought (raisonnement)."""
        if not self._cot_chunks:
            return

        self._cot_visible = not self._cot_visible

        if self._cot_widget:
            if self._cot_visible:
                # Afficher le COT
                cot_content = "".join(self._cot_chunks)
                cot_text = Text()
                cot_text.append("🧠 Raisonnement (Chain of Thought)\n\n", style=f"bold {Colors.BLEU}")
                cot_text.append(cot_content, style=f"italic {Colors.TEXT_DIM}")
                self._cot_widget.update(cot_text)
                self._cot_widget.display = True
            else:
                # Cacher le COT
                self._cot_widget.display = False

    def has_cot(self) -> bool:
        """Retourne True si ce message a du COT."""
        return bool(self._cot_chunks)

    def get_content(self) -> str:
        """Retourne le contenu complet."""
        if self._markdown_widget:
            return str(self._markdown_widget.document) if hasattr(self._markdown_widget, 'document') else ""
        return "".join(self._chunks)


class HistorySearchScreen(ModalScreen[str]):
    """Modal de recherche dans l'historique des prompts (Ctrl+R)."""

    DEFAULT_CSS = """
    HistorySearchScreen {
        align: center middle;
    }

    HistorySearchScreen > Vertical {
        width: 80%;
        max-width: 100;
        height: auto;
        max-height: 80%;
        background: #161B22;
        border: solid #FF7000;
        padding: 1 2;
    }

    HistorySearchScreen #search-input {
        width: 100%;
        margin-bottom: 1;
    }

    HistorySearchScreen #history-list {
        height: auto;
        max-height: 20;
        background: #0D1117;
    }

    HistorySearchScreen .history-item {
        padding: 0 1;
    }

    HistorySearchScreen .history-item:hover {
        background: #21262D;
    }

    HistorySearchScreen .history-item.-selected {
        background: #FF7000;
        color: #0D1117;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Annuler"),
        Binding("enter", "select", "Sélectionner"),
        Binding("up", "cursor_up", "Haut"),
        Binding("down", "cursor_down", "Bas"),
    ]

    def __init__(self, history: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.history = history[::-1]  # Plus récent en premier
        self.filtered: list[str] = self.history.copy()
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(
                Text("Recherche historique (Ctrl+R)", style=f"bold {Colors.ORANGE}"),
                id="search-header"
            )
            yield Input(placeholder="Tapez pour filtrer...", id="search-input")
            yield ListView(id="history-list")
            yield Static(
                Text("↑↓ Naviguer │ Enter Sélectionner │ Esc Annuler", style="dim"),
                id="search-footer"
            )

    def on_mount(self) -> None:
        self._update_list()
        self.query_one("#search-input", Input).focus()

    def _update_list(self) -> None:
        """Met à jour la liste des résultats."""
        list_view = self.query_one("#history-list", ListView)
        list_view.clear()

        for i, item in enumerate(self.filtered[:20]):  # Max 20 items
            truncated = item[:80] + "..." if len(item) > 80 else item
            list_item = ListItem(
                Label(truncated),
                classes="history-item",
                id=f"history-{i}",
            )
            list_view.append(list_item)

        # Sélectionner le premier
        if self.filtered:
            self.selected_index = 0
            list_view.index = 0

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filtre l'historique quand le texte change."""
        query = event.value.lower().strip()
        if query:
            self.filtered = [h for h in self.history if query in h.lower()]
        else:
            self.filtered = self.history.copy()
        self._update_list()

    def action_cancel(self) -> None:
        """Ferme sans sélection."""
        self.dismiss("")

    def action_select(self) -> None:
        """Sélectionne l'item courant."""
        if self.filtered and 0 <= self.selected_index < len(self.filtered):
            self.dismiss(self.filtered[self.selected_index])
        else:
            self.dismiss("")

    def action_cursor_up(self) -> None:
        """Monte dans la liste."""
        if self.selected_index > 0:
            self.selected_index -= 1
            list_view = self.query_one("#history-list", ListView)
            list_view.index = self.selected_index

    def action_cursor_down(self) -> None:
        """Descend dans la liste."""
        if self.selected_index < len(self.filtered) - 1:
            self.selected_index += 1
            list_view = self.query_one("#history-list", ListView)
            list_view.index = self.selected_index

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Quand on clique sur un item."""
        if event.item and event.item.id:
            idx = int(event.item.id.split("-")[1])
            if 0 <= idx < len(self.filtered):
                self.dismiss(self.filtered[idx])


class ThereseApp(App):
    """Application principale THERESE CLI."""

    CSS = THERESE_CSS

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quitter"),
        Binding("ctrl+l", "clear", "Effacer"),
        Binding("ctrl+r", "history_search", "Historique"),
        Binding("escape", "cancel", "Annuler"),
        Binding("ctrl+t", "tree", "Tree"),
        Binding("ctrl+g", "git_status", "Git"),
        Binding("ctrl+o", "toggle_cot", "COT"),
        Binding("ctrl+shift+r", "reset", "Reset"),
    ]

    def __init__(self, working_dir: Path | None = None) -> None:
        super().__init__()
        if working_dir:
            config.working_dir = working_dir
        self.agent = ThereseAgent()
        self.is_processing = False
        self.status_bar: StatusBar | None = None
        self._last_streaming_msg: StreamingMessage | None = None  # Pour toggle COT
        self._last_escape_time: float = 0.0  # Pour détecter double Esc (quick rewind)

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

        # Zone de saisie expandable
        with Vertical(id="input-area"):
            yield ExpandableInput(
                placeholder="Message ou /commande... (Ctrl+J = nouvelle ligne)",
                id="input",
            )

        # Status bar
        self.status_bar = StatusBar(self.agent, id="status")
        yield self.status_bar

        yield Footer()

    def on_mount(self) -> None:
        """Au montage de l'app."""
        # Focus sur l'input
        self.query_one("#input", ExpandableInput).focus()

        # Afficher le grand logo coloré
        conversation = self.query_one("#conversation", ScrollableContainer)
        conversation.mount(BigLogo(id="big-logo"))

        # Message de bienvenue simplifié
        welcome = f"""**Répertoire:** `{config.working_dir}`

**Commandes:** `/help` `/init` `/tree` `/status` `/tasks`
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

    def _is_slash_command(self, text: str) -> bool:
        """Vérifie si le texte est une commande slash (pas un chemin)."""
        if not text.startswith("/"):
            return False
        # Commande slash = /mot (sans autre / dedans avant un espace)
        # Chemin = /Users/... ou /home/... (contient un autre /)
        first_part = text.split()[0] if text.split() else text
        # Si le premier "mot" contient un autre /, c'est un chemin
        if "/" in first_part[1:]:
            return False
        return True

    async def on_expandable_input_submitted(self, event: ExpandableInput.Submitted) -> None:
        """Quand l'utilisateur soumet un message."""
        if self.is_processing:
            return

        user_input = event.value.strip()
        file_paths = event.file_paths
        image_paths = event.image_paths

        if not user_input and not file_paths and not image_paths:
            return

        # Vérifier si c'est une commande slash (pas un chemin comme /Users/...)
        if self._is_slash_command(user_input):
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
                elif response.startswith("__EXPORT__:"):
                    filename = response.split(":", 1)[1]
                    result = self._export_conversation(filename)
                    self._add_message(result, "command")
                    return

                self._add_message(user_input, "user")
                self._add_message(response, "command")
                return

        # Construire le message avec les chemins détectés
        display_msg = user_input

        # Ajouter les chemins de fichiers détectés au message
        if file_paths:
            paths_info = "\n".join([f"📁 `{p}`" for p in file_paths])
            display_msg = f"{user_input}\n\n{paths_info}" if user_input else paths_info
            # Enrichir le prompt avec le contenu des fichiers (si texte)
            if not user_input:
                user_input = f"Voici les fichiers/dossiers suivants:\n" + "\n".join(file_paths)
            else:
                user_input += f"\n\nChemins détectés:\n" + "\n".join(file_paths)

        # Ajouter les images détectées
        if image_paths:
            imgs_info = "\n".join([f"🖼️ `{Path(p).name}`" for p in image_paths])
            display_msg = f"{display_msg}\n\n{imgs_info}" if display_msg else imgs_info
            if not user_input or user_input == display_msg:
                user_input = "Analyse cette image." if len(image_paths) == 1 else "Analyse ces images."

        # Étape 1: Afficher le message utilisateur et laisser l'UI se rendre
        self._add_message(display_msg, "user")
        self.is_processing = True

        # Étape 2: Différer la création du message streaming (après rendu du msg user)
        self.set_timer(0.05, lambda: self._show_thinking_then_process(user_input, image_paths))

    def _show_thinking_then_process(
        self, user_input: str, images: list[str] | None = None
    ) -> None:
        """Affiche le message de réflexion puis lance l'API."""
        conversation = self.query_one("#conversation", ScrollableContainer)
        streaming_msg = self._add_streaming_message()

        # Forcer le scroll en bas
        conversation.scroll_end(animate=False)
        self.refresh()

        # Étape 3: Différer l'appel API (après rendu du msg streaming)
        self.set_timer(0.1, lambda: self._process_request(user_input, streaming_msg, images))

    @work(exclusive=True, thread=True)
    def _process_request(
        self, user_input: str, streaming_msg: StreamingMessage, images: list[str] | None = None
    ) -> None:
        """Traite une requête dans un thread séparé (100% synchrone)."""
        import time
        from textual.worker import get_current_worker

        worker = get_current_worker()

        try:
            self.call_from_thread(streaming_msg.start_stream_sync)

            chunk_count = 0
            last_status_update = time.time()

            # Utiliser chat_sync (synchrone) - pas de problème d'event loop!
            for chunk in self.agent.chat_sync(user_input, images=images):
                if worker.is_cancelled:
                    break
                # Ajouter le chunk via call_from_thread
                self.call_from_thread(streaming_msg.append_sync, chunk)
                chunk_count += 1

                # Scroll régulièrement
                if chunk_count % 3 == 0:
                    self.call_from_thread(self._scroll_to_bottom)

                # Mise à jour status bar toutes les secondes
                now = time.time()
                if (now - last_status_update) >= 1.0:
                    self.call_from_thread(streaming_msg._update_status)
                    last_status_update = now

            self.call_from_thread(streaming_msg.stop_stream_sync)

        except Exception as e:
            self.call_from_thread(streaming_msg.append_sync, f"\n\n**Erreur:** {e}")
            self.call_from_thread(streaming_msg.stop_stream_sync)

        finally:
            self.call_from_thread(self._finish_processing)

    def _scroll_to_bottom(self) -> None:
        """Scroll en bas (appelé depuis le thread principal)."""
        conversation = self.query_one("#conversation", ScrollableContainer)
        # Forcer le layout avant de scroller pour que le contenu soit rendu
        self.refresh(layout=True)
        conversation.scroll_end(animate=False)

    def _finish_processing(self) -> None:
        """Finalise le traitement (appelé depuis le thread principal)."""
        self.is_processing = False
        conversation = self.query_one("#conversation", ScrollableContainer)
        conversation.scroll_end(animate=True)
        if self.status_bar:
            self.status_bar.refresh_stats()
        self.query_one("#input", ExpandableInput).focus()

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
        """Annule l'opération en cours ou quick rewind (double Esc)."""
        import time

        now = time.time()

        # Double Esc (moins de 500ms) = quick rewind
        if (now - self._last_escape_time) < 0.5:
            self._quick_rewind()
            self._last_escape_time = 0.0  # Reset
            return

        self._last_escape_time = now

        if self.is_processing:
            self.notify("Annulation en cours...")
        else:
            self.notify("Esc x2 = quick rewind", severity="information")

    def _quick_rewind(self) -> None:
        """Quick rewind au dernier checkpoint."""
        if not self.agent.checkpoint_manager:
            self.notify("Checkpoints non disponibles", severity="warning")
            return

        success, message = self.agent.checkpoint_manager.rewind()
        if success:
            self.notify(f"Rewind: {message}", severity="information")
            self._add_message(f"Rewind effectué: {message}", "command")
        else:
            self.notify(message, severity="warning")

    async def action_tree(self) -> None:
        """Affiche l'arborescence."""
        _, response = await process_slash_command("/tree")
        self._add_message(response, "command")

    async def action_git_status(self) -> None:
        """Affiche le statut Git."""
        _, response = await process_slash_command("/status")
        self._add_message(response, "command")

    def action_toggle_cot(self) -> None:
        """Affiche/cache le Chain of Thought du dernier message."""
        if self._last_streaming_msg and self._last_streaming_msg.has_cot():
            self._last_streaming_msg.toggle_cot()
        else:
            self.notify("Pas de raisonnement à afficher", severity="warning")

    def action_history_search(self) -> None:
        """Ouvre la recherche dans l'historique (Ctrl+R)."""
        history = ExpandableInput._history
        if not history:
            self.notify("Historique vide", severity="warning")
            return

        def on_dismiss(result: str) -> None:
            if result:
                # Insérer dans l'input
                input_widget = self.query_one("#input", ExpandableInput)
                input_widget.text = result
                input_widget.focus()

        self.push_screen(HistorySearchScreen(history), on_dismiss)

    def _export_conversation(self, filename: str) -> str:
        """Exporte la conversation en fichier Markdown."""
        from datetime import datetime

        # Construire le contenu Markdown
        lines = [
            f"# Conversation THÉRÈSE",
            f"",
            f"**Exporté le:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Modèle:** {self.agent.config.model}",
            f"**Messages:** {len(self.agent.messages)}",
            f"",
            "---",
            "",
        ]

        for msg in self.agent.messages:
            if msg.role == "system":
                continue  # Pas besoin d'exporter le system prompt
            elif msg.role == "user":
                lines.append(f"## 👤 Utilisateur\n")
                lines.append(msg.content or "")
                lines.append("")
            elif msg.role == "assistant":
                lines.append(f"## 🤖 THÉRÈSE\n")
                lines.append(msg.content or "")
                if msg.tool_calls:
                    lines.append("\n**Outils utilisés:**")
                    for tc in msg.tool_calls:
                        lines.append(f"- `{tc['function']['name']}`")
                lines.append("")
            elif msg.role == "tool":
                lines.append(f"### 🔧 Résultat: {msg.name}\n")
                # Tronquer les résultats longs
                content = msg.content or ""
                if len(content) > 1000:
                    content = content[:1000] + "\n... (tronqué)"
                lines.append(f"```\n{content}\n```\n")

        lines.extend([
            "---",
            "",
            f"*Exporté avec THÉRÈSE CLI v{self.agent.config.model}*",
        ])

        # Écrire le fichier
        export_path = config.working_dir / filename
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            return f"✅ Conversation exportée dans:\n`{export_path}`"
        except Exception as e:
            return f"❌ Erreur d'export: {e}"

