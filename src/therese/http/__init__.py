"""
Serveur HTTP pour THÉRÈSE CLI.

Expose une API REST compatible OpenAI pour permettre
l'intégration avec des outils externes (VS Code, etc.)

Usage:
    therese serve --port 3000

Endpoints:
    POST /v1/chat/completions  - Chat avec streaming SSE
    GET  /v1/models            - Liste des modèles
    GET  /health               - Health check
"""

from .server import create_app, ThereseHTTPServer

__all__ = ["create_app", "ThereseHTTPServer"]
