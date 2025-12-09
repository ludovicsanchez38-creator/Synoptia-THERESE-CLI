"""
Configuration MCP pour THÉRÈSE.

Gère le fichier ~/.therese/mcp.yaml
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml


TransportType = Literal["stdio", "http", "sse"]


@dataclass
class MCPServerConfig:
    """Configuration d'un serveur MCP."""

    name: str
    transport: TransportType = "stdio"
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)

    # Pour transport HTTP
    url: str | None = None

    # Options
    enabled: bool = True
    timeout: int = 30

    def resolve_env(self) -> dict[str, str]:
        """
        Résout les variables d'environnement dans la config.

        ${VAR} → valeur de la variable VAR
        """
        resolved = {}
        for key, value in self.env.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                resolved[key] = os.environ.get(var_name, "")
            else:
                resolved[key] = value
        return resolved


@dataclass
class MCPConfig:
    """Configuration globale MCP."""

    servers: dict[str, MCPServerConfig] = field(default_factory=dict)
    config_path: Path = field(default_factory=lambda: Path.home() / ".therese" / "mcp.yaml")

    @classmethod
    def load(cls, path: Path | str | None = None) -> "MCPConfig":
        """
        Charge la configuration depuis un fichier YAML.

        Args:
            path: Chemin vers le fichier (défaut: ~/.therese/mcp.yaml)

        Returns:
            Instance MCPConfig
        """
        config_path = Path(path) if path else Path.home() / ".therese" / "mcp.yaml"

        config = cls(config_path=config_path)

        if not config_path.exists():
            return config

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}

            servers_data = data.get("servers", {})
            for name, server_data in servers_data.items():
                config.servers[name] = MCPServerConfig(
                    name=name,
                    transport=server_data.get("transport", "stdio"),
                    command=server_data.get("command", ""),
                    args=server_data.get("args", []),
                    env=server_data.get("env", {}),
                    url=server_data.get("url"),
                    enabled=server_data.get("enabled", True),
                    timeout=server_data.get("timeout", 30),
                )

        except Exception as e:
            print(f"Erreur lecture config MCP: {e}")

        return config

    def save(self) -> None:
        """Sauvegarde la configuration."""
        # Créer le répertoire si nécessaire
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "servers": {
                name: {
                    "transport": server.transport,
                    "command": server.command,
                    "args": server.args,
                    "env": server.env,
                    "url": server.url,
                    "enabled": server.enabled,
                    "timeout": server.timeout,
                }
                for name, server in self.servers.items()
            }
        }

        with open(self.config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def add_server(self, server: MCPServerConfig) -> None:
        """Ajoute un serveur."""
        self.servers[server.name] = server

    def remove_server(self, name: str) -> bool:
        """Supprime un serveur."""
        if name in self.servers:
            del self.servers[name]
            return True
        return False

    def get_enabled_servers(self) -> dict[str, MCPServerConfig]:
        """Retourne les serveurs activés."""
        return {
            name: server
            for name, server in self.servers.items()
            if server.enabled
        }


# Configurations par défaut pour les serveurs MCP populaires
DEFAULT_MCP_SERVERS = {
    "filesystem": MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", str(Path.home())],
    ),
    "github": MCPServerConfig(
        name="github",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
    ),
    "notion": MCPServerConfig(
        name="notion",
        transport="stdio",
        command="npx",
        args=["-y", "@notionhq/mcp-server"],
        env={"NOTION_TOKEN": "${NOTION_TOKEN}"},
    ),
    "postgres": MCPServerConfig(
        name="postgres",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres"],
        env={"DATABASE_URL": "${DATABASE_URL}"},
    ),
    "fetch": MCPServerConfig(
        name="fetch",
        transport="stdio",
        command="npx",
        args=["-y", "@anthropic/mcp-server-fetch"],
    ),
}
