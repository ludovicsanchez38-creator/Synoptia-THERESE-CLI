"""
Outils système pour THERESE CLI.

Chaque outil est défini avec :
- Une fonction Python qui exécute l'action
- Un schéma JSON pour le function calling Mistral

Outils disponibles (18 total):
- Fichiers: read_file, write_file, edit_file, glob, grep
- Système: bash, tree
- Web: web_fetch, web_search
- Git: git, git_commit, git_status
- Diff: diff, diff_preview
- Projet: project_detect, project_run
- Tâches: task_list, task_add, task_update
"""

from .base import Tool, ToolResult

# Imports des outils
from .bash import BashTool
from .edit import EditTool
from .glob_tool import GlobTool
from .grep import GrepTool
from .read import ReadTool
from .write import WriteTool
from .tree import TreeTool
from .web import WebFetchTool, WebSearchTool
from .git import GitTool, GitCommitTool, GitStatusTool
from .diff import DiffTool, DiffPreviewTool
from .project import ProjectDetectTool, ProjectRunTool
from .task import TaskListTool, TaskAddTool, TaskUpdateTool
from .subagent import SubAgentTool, ListAgentsTool

# Registre de tous les outils disponibles
TOOLS: dict[str, Tool] = {}


def register_tool(tool: Tool) -> None:
    """Enregistre un outil dans le registre global."""
    TOOLS[tool.name] = tool


def get_all_tools() -> list[Tool]:
    """Retourne tous les outils enregistrés."""
    return list(TOOLS.values())


def get_tool(name: str) -> Tool | None:
    """Récupère un outil par son nom."""
    return TOOLS.get(name)


def get_tools_schema() -> list[dict]:
    """Retourne les schémas de tous les outils pour Mistral."""
    return [tool.to_mistral_schema() for tool in TOOLS.values()]


def get_tools_summary() -> str:
    """Retourne un résumé des outils pour le prompt système."""
    categories = {
        "📁 Fichiers": ["read_file", "write_file", "edit_file", "glob", "grep"],
        "🖥️ Système": ["bash", "tree"],
        "🌐 Web": ["web_fetch", "web_search"],
        "📊 Git": ["git", "git_commit", "git_status"],
        "🔄 Diff": ["diff", "diff_preview"],
        "📦 Projet": ["project_detect", "project_run"],
        "✅ Tâches": ["task_list", "task_add", "task_update"],
        "🤖 Agents": ["spawn_subagent", "list_agents"],
    }

    lines = []
    for category, tool_names in categories.items():
        tools_desc = []
        for name in tool_names:
            tool = TOOLS.get(name)
            if tool:
                tools_desc.append(f"`{name}`")
        if tools_desc:
            lines.append(f"- {category}: {', '.join(tools_desc)}")

    return "\n".join(lines)


# Enregistrement des outils par défaut
def _register_default_tools() -> None:
    """Enregistre les outils par défaut."""
    # Fichiers
    register_tool(ReadTool())
    register_tool(WriteTool())
    register_tool(EditTool())
    register_tool(GlobTool())
    register_tool(GrepTool())

    # Système
    register_tool(BashTool())
    register_tool(TreeTool())

    # Web
    register_tool(WebFetchTool())
    register_tool(WebSearchTool())

    # Git
    register_tool(GitTool())
    register_tool(GitCommitTool())
    register_tool(GitStatusTool())

    # Diff
    register_tool(DiffTool())
    register_tool(DiffPreviewTool())

    # Projet
    register_tool(ProjectDetectTool())
    register_tool(ProjectRunTool())

    # Tâches
    register_tool(TaskListTool())
    register_tool(TaskAddTool())
    register_tool(TaskUpdateTool())

    # Sub-agents
    register_tool(SubAgentTool())
    register_tool(ListAgentsTool())


_register_default_tools()

__all__ = [
    "Tool",
    "ToolResult",
    "TOOLS",
    "register_tool",
    "get_all_tools",
    "get_tool",
    "get_tools_schema",
    "get_tools_summary",
]
