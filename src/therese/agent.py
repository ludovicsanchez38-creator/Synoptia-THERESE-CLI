"""
Agent THERESE - Moteur de raisonnement multi-provider.

Gère la boucle de conversation, le function calling,
le mode ultrathink, la mémoire projet, et les commandes slash.
Support des images via Mistral Vision (Pixtral).

Providers supportés:
- Mistral API (cloud) - défaut
- Ollama (local)
"""

import base64
import json
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

from .config import ThereseConfig, config
from .memory import get_memory_manager
from .providers import ProviderBase, StreamChunk, get_provider
from .tools import TOOLS, get_tools_schema, get_tools_summary
from .tools.project import detect_project
from .checkpoints import CheckpointManager


@dataclass
class Message:
    """Message dans la conversation."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    name: str | None = None
    images: list[str] | None = None  # Liste de chemins d'images


# Extensions d'images supportées par Mistral Vision
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def encode_image_to_base64(image_path: str) -> tuple[str, str]:
    """
    Encode une image en base64 pour l'API Mistral Vision.

    Returns:
        Tuple (base64_data, mime_type)
    """
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image non trouvée: {image_path}")

    # Détecter le type MIME
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        mime_type = "image/png"  # Fallback

    # Lire et encoder en base64
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")

    return data, mime_type


def is_image_path(path: str) -> bool:
    """Vérifie si un chemin pointe vers une image."""
    try:
        p = Path(path).expanduser()
        return p.suffix.lower() in IMAGE_EXTENSIONS
    except Exception:
        return False


@dataclass
class TokenUsage:
    """Suivi de l'utilisation des tokens."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion

    def estimate_cost(self, model: str = "devstral-2") -> float:
        """Estime le coût en USD."""
        # Prix Mistral (décembre 2025)
        prices = {
            # Devstral 2 (code agents) - déc 2025
            "devstral-2": (0.0004, 0.002),  # $0.40/$2.00 per M tokens
            "devstral-small-2": (0.0001, 0.0003),  # $0.10/$0.30 per M tokens
            # Chat models
            "mistral-large-latest": (0.002, 0.006),  # input, output per 1K tokens
            "mistral-large-3-25-12": (0.002, 0.006),
            "mistral-small-latest": (0.0002, 0.0006),
            # Code models (legacy)
            "codestral-latest": (0.001, 0.003),
        }
        input_price, output_price = prices.get(model, (0.0004, 0.002))
        return (self.prompt_tokens * input_price + self.completion_tokens * output_price) / 1000


@dataclass
class ThereseAgent:
    """Agent principal THERESE."""

    config: ThereseConfig = field(default_factory=lambda: config)
    messages: list[Message] = field(default_factory=list)
    provider: ProviderBase | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    checkpoint_manager: CheckpointManager | None = None

    def __post_init__(self) -> None:
        """Initialise le provider et le checkpoint manager."""
        self.config.validate()
        self._init_provider()
        self._init_checkpoint_manager()
        self._add_system_prompt()

    def _init_checkpoint_manager(self) -> None:
        """Initialise le gestionnaire de checkpoints."""
        try:
            self.checkpoint_manager = CheckpointManager(self.config.working_dir)
        except Exception:
            self.checkpoint_manager = None

    def _init_provider(self) -> None:
        """Initialise le provider LLM selon la config."""
        if self.config.provider == "ollama":
            self.provider = get_provider(
                "ollama",
                base_url=self.config.ollama_base_url,
            )
        else:
            self.provider = get_provider(
                "mistral",
                api_key=self.config.api_key,
            )

    def _get_project_context(self) -> str:
        """Récupère le contexte du projet."""
        try:
            info = detect_project(self.config.working_dir)
            memory = get_memory_manager(self.config.working_dir)

            context = f"""
## Projet actuel
- **Nom:** {info.name}
- **Type:** {info.type}
- **Langage:** {info.language}
- **Package Manager:** {info.package_manager or 'N/A'}
"""
            if info.frameworks:
                context += f"- **Frameworks:** {', '.join(info.frameworks)}\n"

            if info.scripts:
                context += "\n**Scripts disponibles:** " + ", ".join(list(info.scripts.keys())[:5])

            # Ajouter la mémoire si elle existe
            memory_context = memory.get_context()
            if memory_context:
                context += "\n" + memory_context

            return context
        except Exception:
            return ""

    def _add_system_prompt(self) -> None:
        """Ajoute le prompt système."""
        tools_summary = get_tools_summary()
        project_context = self._get_project_context()

        system_prompt = f"""Tu es THÉRÈSE, un assistant de programmation expert propulsé par Mistral 3.

████████╗██╗  ██╗███████╗██████╗ ███████╗███████╗███████╗
╚══██╔══╝██║  ██║██╔════╝██╔══██╗██╔════╝██╔════╝██╔════╝
   ██║   ███████║█████╗  ██████╔╝█████╗  ███████╗█████╗
   ██║   ██╔══██║██╔══╝  ██╔══██╗██╔══╝  ╚════██║██╔══╝
   ██║   ██║  ██║███████╗██║  ██║███████╗███████║███████╗
   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝

🇫🇷 Tu es française, tu parles français, tu codes comme une chef.

## Ton rôle
Tu aides les développeurs à :
- Explorer et comprendre leur codebase
- Lire, écrire et modifier des fichiers
- Exécuter des commandes shell
- Gérer Git (commits, branches, status)
- Rechercher sur le web
- Détecter et configurer des projets
- Suivre les tâches en cours

## Répertoire de travail
`{self.config.working_dir}`

{project_context}

## Tes outils ({len(TOOLS)} disponibles)
{tools_summary}

## Commandes slash
L'utilisateur peut utiliser des commandes commençant par `/`:
- `/help` : Affiche l'aide
- `/init` : Initialise THERESE pour le projet
- `/status` : Statut Git
- `/tree` : Arborescence
- `/tasks` : Tâches en cours
- `/memory` : Mémoire projet
- `/model` : Changer de modèle
- `/mode` : Mode d'approbation (auto/safe/yolo)

## Mode d'approbation actuel: `{self.config.mode}`
- `auto`: Confirmation pour les actions dangereuses
- `safe`: Confirmation pour toutes les modifications
- `yolo`: Aucune confirmation

## Règles d'or
1. **Lis TOUJOURS** un fichier avant de le modifier
2. Utilise `diff_preview` avant les modifications importantes
3. Utilise `task_add` pour planifier les tâches complexes
4. Sois concis et direct dans tes réponses
5. En cas d'erreur, analyse et réessaie
6. Parle français, code proprement
7. Utilise `git_status` avant les commits

## Style
- Réponses courtes et directes
- Markdown pour le formatage
- Citations de code avec numéros de ligne
- Pas d'emojis sauf si demandé

Allez, au boulot !"""

        self.messages.append(Message(role="system", content=system_prompt))

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Exécute un outil et retourne le résultat (async)."""
        tool = TOOLS.get(name)
        if not tool:
            return f"Erreur: outil '{name}' non trouvé"

        try:
            result = await tool.execute(**arguments)

            # Tracker les changements dans la mémoire
            if name in ("write_file", "edit_file") and result.success:
                memory = get_memory_manager(self.config.working_dir)
                file_path = arguments.get("file_path", "unknown")
                memory.add_change(f"Modifié: {file_path}")

            return result.to_string()
        except Exception as e:
            return f"Erreur d'exécution de {name}: {e}"

    def _execute_tool_sync(self, name: str, arguments: dict[str, Any]) -> str:
        """Exécute un outil de manière synchrone (pour chat_sync)."""
        import asyncio

        tool = TOOLS.get(name)
        if not tool:
            return f"Erreur: outil '{name}' non trouvé"

        try:
            # Auto-checkpoint AVANT les modifications de fichiers
            if name in ("write_file", "edit_file") and self.checkpoint_manager:
                file_path = arguments.get("file_path", "unknown")
                try:
                    self.checkpoint_manager.track_file(Path(file_path))
                    self.checkpoint_manager.auto_checkpoint(before_action=f"{name} {file_path}")
                except Exception:
                    pass  # Ne pas bloquer si checkpoint échoue

            # Nettoyer toute loop existante avant d'en créer une nouvelle
            try:
                asyncio.set_event_loop(None)
            except Exception:
                pass

            # Créer une nouvelle event loop isolée
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(tool.execute(**arguments))
            finally:
                loop.close()
                asyncio.set_event_loop(None)

            # Tracker les changements dans la mémoire
            if name in ("write_file", "edit_file") and result.success:
                memory = get_memory_manager(self.config.working_dir)
                file_path = arguments.get("file_path", "unknown")
                memory.add_change(f"Modifié: {file_path}")

            return result.to_string()
        except Exception as e:
            return f"Erreur d'exécution de {name}: {e}"

    def _get_ollama_tools(self) -> list[dict]:
        """Retourne un subset de tools essentiels pour Ollama.

        21 tools = trop de contexte pour les modèles locaux.
        On garde les 8 outils les plus importants pour le coding.
        """
        essential_tools = [
            "read_file",    # Lire du code
            "write_file",   # Écrire du code
            "edit_file",    # Modifier du code
            "bash",         # Exécuter des commandes
            "tree",         # Explorer le projet
            "grep",         # Rechercher dans le code
            "glob",         # Trouver des fichiers
            "git_status",   # Voir l'état Git
        ]

        all_tools = get_tools_schema()
        return [t for t in all_tools if t["function"]["name"] in essential_tools]

    def _messages_to_provider_format(self, images: list[str] | None = None) -> list[dict]:
        """Convertit les messages au format générique pour les providers."""
        result = []
        for msg in self.messages:
            msg_dict = {
                "role": msg.role,
                "content": msg.content,
            }
            if msg.images:
                # Encoder les images en base64 pour le provider
                encoded_images = []
                for img_path in msg.images:
                    try:
                        b64_data, mime_type = encode_image_to_base64(img_path)
                        encoded_images.append({
                            "url": f"data:{mime_type};base64,{b64_data}",
                            "base64": b64_data,
                        })
                    except Exception:
                        pass
                if encoded_images:
                    msg_dict["images"] = encoded_images
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            if msg.name:
                msg_dict["name"] = msg.name
            result.append(msg_dict)
        return result

    def chat_sync(
        self, user_input: str, images: list[str] | None = None
    ):
        """
        Version SYNCHRONE de chat() pour éviter les problèmes d'event loop.

        Utilise le provider configuré (Mistral API ou Ollama).
        Doit être appelée depuis un thread séparé.

        Yields des chunks de texte pour l'affichage streaming.
        """
        import asyncio

        # IMPORTANT: Nettoyer toute référence à une event loop existante
        try:
            asyncio.set_event_loop(None)
        except Exception:
            pass

        # Recréer le provider (thread safety)
        self._init_provider()

        # FIX: Vérifier si le dernier message est un "tool"
        if self.messages and self.messages[-1].role == "tool":
            self.messages.append(Message(
                role="assistant",
                content="(Reprise de la conversation après interruption)"
            ))

        # Ajouter le message utilisateur (avec images si présentes)
        self.messages.append(Message(role="user", content=user_input, images=images))

        # Déterminer le modèle selon le provider
        if self.config.provider == "ollama":
            model = self.config.ollama_model
        else:
            # Utiliser Pixtral pour les images (Mistral), sinon le modèle par défaut
            model = "pixtral-large-latest" if images else self.config.model

        max_iterations = 15

        for iteration in range(max_iterations):
            # Préparer les messages pour le provider
            provider_messages = self._messages_to_provider_format(images)

            # Préparer les tools (sauf première itération avec images sur Mistral)
            tools = None
            if not (images and iteration == 0 and self.config.provider == "mistral"):
                if self.provider and self.provider.supports_tools:
                    # Ollama : subset de tools essentiels (21 tools = trop pour le contexte)
                    if self.config.provider == "ollama":
                        tools = self._get_ollama_tools()
                    else:
                        tools = get_tools_schema()

            # Appel streaming via le provider
            content_chunks: list[str] = []
            tool_calls: list[dict] = []

            try:
                for chunk in self.provider.chat_stream(
                    messages=provider_messages,
                    model=model if iteration == 0 else self.config.get_active_model(),
                    tools=tools,
                ):
                    # Contenu textuel
                    if chunk.content:
                        content_chunks.append(chunk.content)
                        yield chunk.content

                    # Tool calls
                    if chunk.tool_calls:
                        tool_calls = chunk.tool_calls

                    # Usage
                    if chunk.usage:
                        self.usage.add(
                            chunk.usage.get("prompt_tokens", 0),
                            chunk.usage.get("completion_tokens", 0),
                        )

            except Exception as e:
                yield f"\n\n❌ Erreur provider: {e}"
                return

            full_content = "".join(content_chunks)

            # Si pas de tool calls, on a fini
            if not tool_calls:
                self.messages.append(Message(
                    role="assistant",
                    content=full_content,
                ))
                break

            # Ajouter le message assistant avec tool calls
            self.messages.append(Message(
                role="assistant",
                content=full_content,
                tool_calls=tool_calls,
            ))

            # Exécuter les outils (de manière synchrone)
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                yield f"\n\n⚙️  **{func_name}**"
                if func_args:
                    args_preview = []
                    for k, v in func_args.items():
                        v_str = repr(v)
                        if len(v_str) > 40:
                            v_str = v_str[:40] + "..."
                        args_preview.append(f"{k}={v_str}")
                    yield f"({', '.join(args_preview)})\n"
                else:
                    yield "()\n"

                # Exécuter l'outil de manière synchrone
                result = self._execute_tool_sync(func_name, func_args)

                lines = result.split("\n")
                if len(lines) > 30:
                    result_preview = "\n".join(lines[:30]) + f"\n... ({len(lines) - 30} lignes de plus)"
                elif len(result) > 2000:
                    result_preview = result[:2000] + "..."
                else:
                    result_preview = result

                yield f"\n{result_preview}\n"

                self.messages.append(Message(
                    role="tool",
                    content=result,
                    tool_call_id=tc["id"],
                    name=func_name,
                ))

        else:
            yield "\n\n⚠️ Limite d'itérations atteinte. La tâche est peut-être trop complexe."

        # Auto-compact si nécessaire (après la réponse)
        compacted, compact_msg = self.auto_compact()
        if compacted:
            yield f"\n\n{compact_msg}"

    def reset(self) -> None:
        """Réinitialise la conversation."""
        self.messages.clear()
        self._add_system_prompt()

    def _should_auto_compact(self) -> bool:
        """Vérifie si on doit auto-compacter basé sur les tokens."""
        if not self.config.auto_compact:
            return False
        threshold = int(self.config.max_context_tokens * self.config.compact_threshold)
        return self.usage.prompt_tokens > threshold

    def _format_messages_for_summary(self, messages: list[Message]) -> str:
        """Formate les messages pour le résumé."""
        formatted = []
        for msg in messages:
            if msg.role == "system":
                continue
            prefix = "👤" if msg.role == "user" else "🤖" if msg.role == "assistant" else "🔧"
            content = msg.content[:500] if msg.content else ""
            if msg.tool_calls:
                tools = [tc["function"]["name"] for tc in msg.tool_calls]
                content += f" [Tools: {', '.join(tools)}]"
            formatted.append(f"{prefix} {content}")
        return "\n\n".join(formatted)

    def _generate_summary_sync(self, messages: list[Message]) -> str:
        """Génère un résumé LLM des messages (sync)."""
        formatted = self._format_messages_for_summary(messages)
        summary_prompt = f"""Résume cette conversation en 3-5 points clés.
Garde les informations importantes : fichiers modifiés, décisions prises, problèmes résolus.
Sois concis (max 300 mots).

Conversation:
{formatted[:8000]}

Résumé:"""

        try:
            # Utiliser un modèle rapide selon le provider
            if self.config.provider == "ollama":
                model = "ministral-3:3b"  # Rapide pour résumé
            else:
                model = "mistral-small-latest"

            # Récupérer le résumé via le provider
            summary_parts = []
            for chunk in self.provider.chat_stream(
                messages=[{"role": "user", "content": summary_prompt}],
                model=model,
            ):
                if chunk.content:
                    summary_parts.append(chunk.content)

            return "".join(summary_parts) or "[Résumé indisponible]"
        except Exception as e:
            return f"[Résumé auto: {len(messages)} messages précédents - Erreur: {e}]"

    def auto_compact(self) -> tuple[bool, str]:
        """
        Auto-compacte si nécessaire. Utilise le LLM pour résumer.

        Returns:
            (compacted: bool, message: str)
        """
        if not self._should_auto_compact():
            return False, ""

        if len(self.messages) <= self.config.compact_keep_recent + 2:
            return False, ""

        # Séparer les messages
        system_msg = self.messages[0]
        recent = self.messages[-self.config.compact_keep_recent:]
        old_messages = self.messages[1:-self.config.compact_keep_recent]

        if not old_messages:
            return False, ""

        # S'assurer que recent commence par un message "user" pour un ordre valide
        # Sinon on risque: assistant (résumé) -> tool -> user (invalide)
        while recent and recent[0].role in ("tool", "assistant"):
            recent = recent[1:]

        if not recent:
            return False, ""

        # Générer un résumé intelligent
        summary = self._generate_summary_sync(old_messages)

        # Reconstruire
        old_count = len(self.messages)
        self.messages = [system_msg]
        self.messages.append(Message(
            role="assistant",
            content=f"📝 **Résumé de la conversation précédente:**\n\n{summary}"
        ))
        self.messages.extend(recent)

        # Reset partiel des tokens (estimation)
        self.usage.prompt_tokens = int(self.usage.prompt_tokens * 0.3)

        return True, f"💾 Conversation compactée: {old_count} → {len(self.messages)} messages"

    def compact(self) -> str:
        """Compacte manuellement la conversation avec résumé LLM."""
        if len(self.messages) <= 2:
            return "Conversation trop courte pour être compactée."

        compacted, message = self.auto_compact()
        if compacted:
            return message
        return "Rien à compacter."

    def get_stats(self) -> dict:
        """Retourne les statistiques de la session."""
        return {
            "messages": len(self.messages),
            "tokens": {
                "prompt": self.usage.prompt_tokens,
                "completion": self.usage.completion_tokens,
                "total": self.usage.total_tokens,
            },
            "cost_usd": round(self.usage.estimate_cost(self.config.model), 4),
            "model": self.config.model,
            "mode": self.config.mode,
        }
