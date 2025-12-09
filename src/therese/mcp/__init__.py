"""
Support MCP (Model Context Protocol) pour THÉRÈSE.

MCP est un standard ouvert introduit par Anthropic (nov 2024)
pour connecter des outils externes aux LLMs de manière standardisée.

Permet d'étendre THÉRÈSE avec :
- Serveurs MCP externes (GitHub, Notion, PostgreSQL, etc.)
- Tools personnalisés
- Ressources et prompts

Configuration: ~/.therese/mcp.yaml

Usage:
    therese mcp-list              # Liste serveurs configurés
    therese mcp-test github       # Test connexion
"""

from .manager import MCPManager
from .config import MCPConfig, MCPServerConfig

__all__ = ["MCPManager", "MCPConfig", "MCPServerConfig"]
