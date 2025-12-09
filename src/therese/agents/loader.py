"""
Chargeur de Custom Agents depuis fichiers YAML.

Les agents peuvent être définis dans:
- ~/.therese/agents/*.yaml (agents utilisateur)
- src/therese/agents/builtin/*.yaml (agents intégrés)
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentConfig:
    """Configuration d'un agent personnalisé."""

    name: str
    description: str = ""
    icon: str = "🤖"
    system_prompt: str = ""

    # Modèle spécifique (optionnel)
    model: str | None = None

    # Liste blanche d'outils autorisés (None = tous)
    tools: list[str] | None = None

    # Serveurs MCP à utiliser
    mcp_servers: list[str] = field(default_factory=list)

    # Métadonnées
    author: str = ""
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "AgentConfig":
        """Charge un agent depuis un fichier YAML."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls(
            name=data.get("name", path.stem),
            description=data.get("description", ""),
            icon=data.get("icon", "🤖"),
            system_prompt=data.get("system_prompt", ""),
            model=data.get("model"),
            tools=data.get("tools"),
            mcp_servers=data.get("mcp_servers", []),
            author=data.get("author", ""),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
        )

    def to_yaml(self) -> str:
        """Sérialise l'agent en YAML."""
        data = {
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "system_prompt": self.system_prompt,
        }
        if self.model:
            data["model"] = self.model
        if self.tools:
            data["tools"] = self.tools
        if self.mcp_servers:
            data["mcp_servers"] = self.mcp_servers
        if self.author:
            data["author"] = self.author
        if self.version != "1.0.0":
            data["version"] = self.version
        if self.tags:
            data["tags"] = self.tags

        return yaml.dump(data, default_flow_style=False, allow_unicode=True)


class AgentLoader:
    """Gestionnaire de chargement d'agents."""

    def __init__(self) -> None:
        self.user_agents_dir = Path.home() / ".therese" / "agents"
        self.builtin_agents_dir = Path(__file__).parent / "builtin"
        self._cache: dict[str, AgentConfig] = {}

    def _ensure_dirs(self) -> None:
        """Crée les répertoires si nécessaires."""
        self.user_agents_dir.mkdir(parents=True, exist_ok=True)

    def list_agents(self) -> list[AgentConfig]:
        """Liste tous les agents disponibles."""
        agents = []

        # Agents intégrés
        if self.builtin_agents_dir.exists():
            for yaml_file in self.builtin_agents_dir.glob("*.yaml"):
                try:
                    agent = AgentConfig.from_yaml(yaml_file)
                    agent.tags.append("builtin")
                    agents.append(agent)
                except Exception:
                    pass

        # Agents utilisateur (priorité)
        if self.user_agents_dir.exists():
            for yaml_file in self.user_agents_dir.glob("*.yaml"):
                try:
                    agent = AgentConfig.from_yaml(yaml_file)
                    agent.tags.append("user")
                    agents.append(agent)
                except Exception:
                    pass

        return agents

    def get_agent(self, name: str) -> AgentConfig | None:
        """Récupère un agent par son nom."""
        # Cache
        if name in self._cache:
            return self._cache[name]

        # Chercher dans user d'abord
        user_path = self.user_agents_dir / f"{name}.yaml"
        if user_path.exists():
            agent = AgentConfig.from_yaml(user_path)
            self._cache[name] = agent
            return agent

        # Puis builtin
        builtin_path = self.builtin_agents_dir / f"{name}.yaml"
        if builtin_path.exists():
            agent = AgentConfig.from_yaml(builtin_path)
            self._cache[name] = agent
            return agent

        return None

    def create_agent(self, config: AgentConfig) -> Path:
        """Crée un nouvel agent utilisateur."""
        self._ensure_dirs()
        path = self.user_agents_dir / f"{config.name.lower().replace(' ', '-')}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            f.write(config.to_yaml())
        return path

    def delete_agent(self, name: str) -> bool:
        """Supprime un agent utilisateur."""
        path = self.user_agents_dir / f"{name}.yaml"
        if path.exists():
            path.unlink()
            self._cache.pop(name, None)
            return True
        return False


# Singleton
_loader: AgentLoader | None = None


def get_loader() -> AgentLoader:
    """Récupère le loader singleton."""
    global _loader
    if _loader is None:
        _loader = AgentLoader()
    return _loader


def load_agent(name: str) -> AgentConfig | None:
    """Raccourci pour charger un agent."""
    return get_loader().get_agent(name)
