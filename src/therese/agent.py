"""
Agent THERESE - Moteur de raisonnement avec Mistral 3.

Gère la boucle de conversation, le function calling,
le mode ultrathink, la mémoire projet, et les commandes slash.
"""

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from mistralai import Mistral
from mistralai.models import (
    AssistantMessage,
    SystemMessage,
    ToolMessage,
    UserMessage,
)

from .config import ThereseConfig, config
from .memory import get_memory_manager
from .tools import TOOLS, get_tools_schema, get_tools_summary
from .tools.project import detect_project


@dataclass
class Message:
    """Message dans la conversation."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None
    name: str | None = None


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

    def estimate_cost(self, model: str = "mistral-large-latest") -> float:
        """Estime le coût en USD."""
        # Prix approximatifs Mistral (décembre 2024)
        prices = {
            "mistral-large-latest": (0.002, 0.006),  # input, output per 1K tokens
            "mistral-large-3-25-12": (0.002, 0.006),
            "codestral-latest": (0.001, 0.003),
            "mistral-small-latest": (0.0002, 0.0006),
        }
        input_price, output_price = prices.get(model, (0.002, 0.006))
        return (self.prompt_tokens * input_price + self.completion_tokens * output_price) / 1000


@dataclass
class ThereseAgent:
    """Agent principal THERESE."""

    config: ThereseConfig = field(default_factory=lambda: config)
    messages: list[Message] = field(default_factory=list)
    client: Mistral | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)

    def __post_init__(self) -> None:
        """Initialise le client Mistral."""
        self.config.validate()
        self.client = Mistral(api_key=self.config.api_key)
        self._add_system_prompt()

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

    def _messages_to_mistral(self) -> list:
        """Convertit les messages au format Mistral."""
        result = []
        for msg in self.messages:
            if msg.role == "system":
                result.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                result.append(UserMessage(content=msg.content))
            elif msg.role == "assistant":
                if msg.tool_calls:
                    result.append(AssistantMessage(
                        content=msg.content or "",
                        tool_calls=msg.tool_calls,
                    ))
                else:
                    result.append(AssistantMessage(content=msg.content))
            elif msg.role == "tool":
                result.append(ToolMessage(
                    content=msg.content,
                    tool_call_id=msg.tool_call_id,
                    name=msg.name,
                ))
        return result

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Exécute un outil et retourne le résultat."""
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

    async def chat(self, user_input: str) -> AsyncIterator[str]:
        """
        Envoie un message et stream la réponse.

        Yields des chunks de texte pour l'affichage streaming.
        Gère automatiquement les tool calls.
        """
        # Ajouter le message utilisateur
        self.messages.append(Message(role="user", content=user_input))

        max_iterations = 15  # Augmenté pour les tâches complexes

        for iteration in range(max_iterations):
            # Appel à Mistral avec streaming
            response = self.client.chat.stream(
                model=self.config.model,
                messages=self._messages_to_mistral(),
                tools=get_tools_schema(),
                tool_choice="auto",
            )

            # Collecter la réponse
            content_chunks: list[str] = []
            tool_calls: list[dict] = []

            for event in response:
                if event.data.choices:
                    choice = event.data.choices[0]
                    delta = choice.delta

                    # Contenu textuel
                    if delta.content:
                        content_chunks.append(delta.content)
                        yield delta.content

                    # Tool calls
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            # Gérer l'accumulation des tool calls en streaming
                            if tc.index >= len(tool_calls):
                                tool_calls.append({
                                    "id": tc.id or "",
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name or "",
                                        "arguments": tc.function.arguments or "",
                                    },
                                })
                            else:
                                # Accumuler les arguments
                                if tc.function.arguments:
                                    tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments
                                if tc.function.name:
                                    tool_calls[tc.index]["function"]["name"] = tc.function.name
                                if tc.id:
                                    tool_calls[tc.index]["id"] = tc.id

                # Tracker l'usage
                if event.data.usage:
                    self.usage.add(
                        event.data.usage.prompt_tokens or 0,
                        event.data.usage.completion_tokens or 0,
                    )

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

            # Exécuter les outils
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    func_args = {}

                # Afficher l'appel d'outil
                yield f"\n\n⚙️  **{func_name}**"
                if func_args:
                    # Tronquer les arguments longs
                    args_preview = []
                    for k, v in func_args.items():
                        v_str = repr(v)
                        if len(v_str) > 40:
                            v_str = v_str[:40] + "..."
                        args_preview.append(f"{k}={v_str}")
                    yield f"({', '.join(args_preview)})\n"
                else:
                    yield "()\n"

                # Exécuter l'outil
                result = await self._execute_tool(func_name, func_args)

                # Afficher un résumé du résultat
                lines = result.split("\n")
                if len(lines) > 10:
                    result_preview = "\n".join(lines[:10]) + f"\n... ({len(lines) - 10} lignes de plus)"
                elif len(result) > 500:
                    result_preview = result[:500] + "..."
                else:
                    result_preview = result

                yield f"```\n{result_preview}\n```\n"

                # Ajouter le résultat aux messages
                self.messages.append(Message(
                    role="tool",
                    content=result,
                    tool_call_id=tc["id"],
                    name=func_name,
                ))

        else:
            yield "\n\n⚠️ Limite d'itérations atteinte. La tâche est peut-être trop complexe."

    def reset(self) -> None:
        """Réinitialise la conversation."""
        self.messages.clear()
        self._add_system_prompt()

    def compact(self) -> str:
        """Compacte la conversation en gardant un résumé."""
        if len(self.messages) <= 2:
            return "Conversation trop courte pour être compactée."

        # Garder le système et les 5 derniers échanges
        system_msg = self.messages[0]
        recent = self.messages[-10:]

        # Créer un résumé
        summary = f"[Conversation précédente résumée - {len(self.messages)} messages]"

        self.messages = [system_msg]
        self.messages.append(Message(role="assistant", content=summary))
        self.messages.extend(recent)

        return f"Conversation compactée: {len(self.messages)} messages conservés."

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
