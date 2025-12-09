"""
Système de Custom Agents pour THÉRÈSE.

Permet de créer des agents spécialisés via fichiers YAML.
"""

from .loader import AgentConfig, AgentLoader, load_agent

__all__ = ["AgentConfig", "AgentLoader", "load_agent"]
