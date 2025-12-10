"""
Outil pour spawner des sous-agents spécialisés.

Permet à l'agent principal de déléguer des tâches à des agents
spécialisés (code-reviewer, debugger, planner, etc.).
"""

import json
from typing import Any

from .base import Tool, ToolResult
from ..agents.loader import load_agent, get_loader
from ..config import config


class SubAgentTool(Tool):
    """
    Délègue une tâche à un sous-agent spécialisé.

    Agents disponibles :
    - code-reviewer : Expert en revue de code
    - debugger : Expert en débogage
    - planner : Architecte pour planification
    """

    name = "spawn_subagent"
    description = """Délègue une tâche à un agent spécialisé. Utilise cet outil quand:
- Tu as besoin d'une revue de code approfondie (agent: code-reviewer)
- Tu dois analyser et corriger un bug complexe (agent: debugger)
- Tu dois planifier une implémentation complexe (agent: planner)

L'agent retournera son analyse/résultat."""

    parameters = {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "description": "Nom de l'agent à utiliser (code-reviewer, debugger, planner)",
                "enum": ["code-reviewer", "debugger", "planner"],
            },
            "task": {
                "type": "string",
                "description": "La tâche à exécuter par l'agent (ex: 'Review le fichier src/main.py pour les bugs de sécurité')",
            },
            "context": {
                "type": "string",
                "description": "Contexte additionnel optionnel (code, erreur, etc.)",
            },
        },
        "required": ["agent", "task"],
    }

    async def execute(
        self,
        agent: str,
        task: str,
        context: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        """Exécute la tâche avec le sous-agent spécifié."""
        from ..providers import get_provider

        # Charger la config de l'agent
        agent_config = load_agent(agent)
        if not agent_config:
            available = [a.name for a in get_loader().list_agents()]
            return ToolResult(
                success=False,
                output="",
                error=f"Agent '{agent}' non trouvé. Disponibles: {', '.join(available)}",
            )

        # Construire le prompt pour le sous-agent
        full_task = task
        if context:
            full_task = f"{task}\n\n## Contexte:\n{context}"

        # Utiliser le provider configuré
        provider = get_provider(
            config.provider,
            api_key=config.api_key if config.provider == "mistral" else None,
            base_url=config.ollama_base_url if config.provider == "ollama" else None,
        )

        # Modèle de l'agent ou défaut
        model = agent_config.model or config.get_active_model()

        # Messages pour le sous-agent
        messages = [
            {
                "role": "system",
                "content": agent_config.system_prompt,
            },
            {
                "role": "user",
                "content": full_task,
            },
        ]

        # Préparer les tools autorisés pour cet agent (si spécifiés)
        tools_schema = None
        if agent_config.tools:
            from . import TOOLS
            tools_schema = []
            for tool_name in agent_config.tools:
                tool = TOOLS.get(tool_name)
                if tool:
                    tools_schema.append(tool.to_mistral_schema())

        try:
            # Exécuter le sous-agent (max 3 itérations pour limiter les coûts)
            result_chunks: list[str] = []
            iteration = 0
            max_iterations = 3

            while iteration < max_iterations:
                iteration += 1
                chunk_text = []
                tool_calls = []

                for chunk in provider.chat_stream(
                    messages=messages,
                    model=model,
                    tools=tools_schema,
                ):
                    if chunk.content:
                        chunk_text.append(chunk.content)
                    if chunk.tool_calls:
                        tool_calls = chunk.tool_calls

                content = "".join(chunk_text)
                result_chunks.append(content)

                # Si pas de tool calls, on a fini
                if not tool_calls:
                    break

                # Ajouter le message assistant
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                })

                # Exécuter les tools et ajouter les résultats
                from . import TOOLS
                for tc in tool_calls:
                    func_name = tc["function"]["name"]
                    try:
                        func_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        func_args = {}

                    tool = TOOLS.get(func_name)
                    if tool:
                        tool_result = await tool.execute(**func_args)
                        messages.append({
                            "role": "tool",
                            "content": tool_result.to_string()[:2000],  # Limiter
                            "tool_call_id": tc["id"],
                            "name": func_name,
                        })

            # Assembler le résultat final
            final_result = "\n\n".join(filter(None, result_chunks))

            return ToolResult(
                success=True,
                output=f"""## Résultat de {agent_config.icon} {agent_config.name}

{final_result}

---
*Sous-agent: {agent} | Modèle: {model} | {iteration} itération(s)*""",
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur du sous-agent '{agent}': {e}",
            )


class ListAgentsTool(Tool):
    """Liste les agents disponibles."""

    name = "list_agents"
    description = "Liste tous les agents spécialisés disponibles pour spawn_subagent."

    parameters = {
        "type": "object",
        "properties": {},
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Liste les agents disponibles."""
        agents = get_loader().list_agents()

        if not agents:
            return ToolResult(
                success=True,
                output="Aucun agent disponible.",
            )

        lines = ["# Agents disponibles", ""]
        for agent in agents:
            tag = "builtin" if "builtin" in agent.tags else "user"
            lines.append(f"- **{agent.icon} {agent.name}** [{tag}]")
            lines.append(f"  {agent.description}")
            if agent.model:
                lines.append(f"  *Modèle: {agent.model}*")
            lines.append("")

        return ToolResult(
            success=True,
            output="\n".join(lines),
        )
