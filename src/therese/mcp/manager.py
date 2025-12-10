"""
Gestionnaire de connexions MCP pour THÉRÈSE.

Gère les connexions aux serveurs MCP via stdio ou HTTP,
et expose les tools disponibles pour le function calling.
"""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console

from .config import MCPConfig, MCPServerConfig

console = Console(stderr=True)


@dataclass
class MCPTool:
    """Un outil exposé par un serveur MCP."""

    name: str
    description: str
    input_schema: dict
    server_name: str

    @property
    def full_name(self) -> str:
        """Nom complet avec préfixe serveur."""
        return f"mcp_{self.server_name}_{self.name}"

    def to_mistral_schema(self) -> dict:
        """Convertit en schéma Mistral function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.full_name,
                "description": f"[MCP:{self.server_name}] {self.description}",
                "parameters": self.input_schema,
            },
        }


@dataclass
class MCPServerConnection:
    """Connexion active à un serveur MCP."""

    config: MCPServerConfig
    process: subprocess.Popen | None = None
    tools: list[MCPTool] = field(default_factory=list)
    connected: bool = False
    error: str | None = None

    def __post_init__(self):
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def connect(self) -> bool:
        """
        Établit la connexion au serveur MCP.

        Returns:
            True si connecté avec succès.
        """
        if self.config.transport != "stdio":
            self.error = f"Transport {self.config.transport} non supporté (stdio uniquement)"
            return False

        try:
            # Résoudre les variables d'environnement
            env = {**dict(subprocess.os.environ), **self.config.resolve_env()}

            # Démarrer le processus
            self.process = subprocess.Popen(
                [self.config.command] + self.config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

            # Envoyer la requête d'initialisation
            init_request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                    },
                    "clientInfo": {
                        "name": "therese",
                        "version": "0.3.0",
                    },
                },
            }

            response = await self._send_request(init_request)
            if not response or "error" in response:
                self.error = f"Échec initialisation: {response.get('error', 'Unknown')}"
                return False

            # Envoyer initialized
            await self._send_notification({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            })

            # Lister les tools disponibles
            tools_request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
            }

            tools_response = await self._send_request(tools_request)
            if tools_response and "result" in tools_response:
                tools_data = tools_response["result"].get("tools", [])
                for tool_data in tools_data:
                    self.tools.append(MCPTool(
                        name=tool_data.get("name", "unknown"),
                        description=tool_data.get("description", ""),
                        input_schema=tool_data.get("inputSchema", {}),
                        server_name=self.config.name,
                    ))

            self.connected = True
            return True

        except Exception as e:
            self.error = str(e)
            return False

    async def _send_request(self, request: dict, timeout: float = 30.0) -> dict | None:
        """Envoie une requête JSON-RPC et attend la réponse."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            return None

        try:
            # Envoyer la requête
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            self.process.stdin.flush()

            # Lire la réponse (avec timeout)
            loop = asyncio.get_event_loop()
            response_line = await asyncio.wait_for(
                loop.run_in_executor(None, self.process.stdout.readline),
                timeout=timeout,
            )

            if response_line:
                return json.loads(response_line.decode())
            return None

        except asyncio.TimeoutError:
            return {"error": "Timeout"}
        except Exception as e:
            return {"error": str(e)}

    async def _send_notification(self, notification: dict) -> None:
        """Envoie une notification (pas de réponse attendue)."""
        if not self.process or not self.process.stdin:
            return

        try:
            notification_json = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_json.encode())
            self.process.stdin.flush()
        except Exception:
            pass

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Appelle un tool sur ce serveur.

        Args:
            tool_name: Nom du tool (sans préfixe serveur)
            arguments: Arguments du tool

        Returns:
            Résultat sous forme de string
        """
        if not self.connected:
            return f"Erreur: Serveur {self.config.name} non connecté"

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        response = await self._send_request(request, timeout=self.config.timeout)

        if not response:
            return "Erreur: Pas de réponse du serveur"

        if "error" in response:
            return f"Erreur MCP: {response['error']}"

        result = response.get("result", {})

        # Extraire le contenu de la réponse
        content = result.get("content", [])
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
            return "\n".join(texts)

        return str(result)

    def disconnect(self) -> None:
        """Ferme la connexion."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None
        self.connected = False


class MCPManager:
    """
    Gestionnaire central des connexions MCP.

    Charge la configuration, connecte les serveurs,
    et expose les tools pour le function calling.
    """

    def __init__(self, config: MCPConfig | None = None):
        self.config = config or MCPConfig.load()
        self.connections: dict[str, MCPServerConnection] = {}

    async def connect_all(self) -> dict[str, bool]:
        """
        Connecte tous les serveurs configurés.

        Returns:
            Dict mapping nom → succès
        """
        results = {}

        for name, server_config in self.config.get_enabled_servers().items():
            results[name] = await self.connect_server(name)

        return results

    async def connect_server(self, name: str) -> bool:
        """
        Connecte un serveur spécifique.

        Args:
            name: Nom du serveur

        Returns:
            True si connecté avec succès
        """
        if name not in self.config.servers:
            return False

        server_config = self.config.servers[name]
        connection = MCPServerConnection(config=server_config)

        success = await connection.connect()
        self.connections[name] = connection

        return success

    def disconnect_all(self) -> None:
        """Déconnecte tous les serveurs."""
        for connection in self.connections.values():
            connection.disconnect()
        self.connections.clear()

    def get_all_tools(self) -> list[MCPTool]:
        """Retourne tous les tools de tous les serveurs connectés."""
        tools = []
        for connection in self.connections.values():
            if connection.connected:
                tools.extend(connection.tools)
        return tools

    def get_tools_schema(self) -> list[dict]:
        """Retourne les schémas Mistral de tous les tools."""
        return [tool.to_mistral_schema() for tool in self.get_all_tools()]

    async def call_tool(self, full_name: str, arguments: dict) -> str:
        """
        Appelle un tool par son nom complet.

        Args:
            full_name: Nom complet (mcp_serveur_tool)
            arguments: Arguments du tool

        Returns:
            Résultat
        """
        # Parser le nom: mcp_serveur_tool
        parts = full_name.split("_", 2)
        if len(parts) < 3 or parts[0] != "mcp":
            return f"Erreur: Nom de tool invalide: {full_name}"

        server_name = parts[1]
        tool_name = parts[2]

        if server_name not in self.connections:
            return f"Erreur: Serveur {server_name} non connecté"

        connection = self.connections[server_name]
        return await connection.call_tool(tool_name, arguments)

    def status(self) -> dict:
        """Retourne le statut de tous les serveurs."""
        return {
            name: {
                "connected": conn.connected,
                "tools_count": len(conn.tools),
                "error": conn.error,
            }
            for name, conn in self.connections.items()
        }


# Instance globale (lazy)
_mcp_manager: MCPManager | None = None


def get_mcp_manager() -> MCPManager:
    """Retourne l'instance globale du MCPManager."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
