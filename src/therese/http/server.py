"""
Serveur HTTP FastAPI pour THÉRÈSE.

API compatible OpenAI avec support SSE streaming.
"""

import json
import time
import uuid
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from ..config import config as therese_config


# === MODÈLES PYDANTIC ===

class ChatMessage(BaseModel):
    """Un message dans la conversation."""
    role: str = Field(..., description="Role: system, user, assistant")
    content: str = Field(..., description="Contenu du message")


class ChatRequest(BaseModel):
    """Requête de chat compatible OpenAI."""
    model: str = Field(default="mistral-large-latest", description="Modèle à utiliser")
    messages: list[ChatMessage] = Field(..., description="Historique de conversation")
    stream: bool = Field(default=True, description="Activer le streaming SSE")
    temperature: float = Field(default=0.7, ge=0, le=2, description="Température")
    max_tokens: int | None = Field(default=None, description="Limite de tokens")

    # Options spécifiques THÉRÈSE
    tools: list[dict] | None = Field(default=None, description="Tools pour function calling")
    ultrathink: bool = Field(default=False, description="Mode raisonnement étendu")


class ChatChoice(BaseModel):
    """Un choix de réponse."""
    index: int = 0
    message: ChatMessage | None = None
    delta: dict | None = None
    finish_reason: str | None = None


class ChatUsage(BaseModel):
    """Statistiques d'utilisation."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """Réponse de chat compatible OpenAI."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: ChatUsage | None = None


class ModelInfo(BaseModel):
    """Information sur un modèle."""
    id: str
    object: str = "model"
    created: int = 1700000000
    owned_by: str = "mistral"


class ModelsResponse(BaseModel):
    """Liste des modèles."""
    object: str = "list"
    data: list[ModelInfo]


# === SERVEUR ===

class ThereseHTTPServer:
    """Serveur HTTP THÉRÈSE avec API OpenAI-compatible."""

    # Modèles Mistral disponibles
    MODELS = [
        {"id": "mistral-large-latest", "description": "Flagship - meilleure qualité"},
        {"id": "mistral-medium-latest", "description": "Équilibré qualité/coût"},
        {"id": "mistral-small-latest", "description": "Rapide et économique"},
        {"id": "codestral-latest", "description": "Spécialisé code"},
        {"id": "pixtral-large-latest", "description": "Multimodal - images"},
        {"id": "magistral-medium-2509", "description": "Raisonnement frontier"},
    ]

    def __init__(self):
        self._agent = None

    @property
    def agent(self):
        """Lazy loading de l'agent."""
        if self._agent is None:
            from ..agent import ThereseAgent
            self._agent = ThereseAgent()
        return self._agent

    def reset_agent(self):
        """Réinitialise l'agent."""
        self._agent = None

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[str]:
        """
        Stream la réponse en format SSE compatible OpenAI.

        Yields des événements SSE.
        """
        # Configurer le modèle
        self.agent.config.model = request.model

        # Extraire le dernier message utilisateur
        user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        # Générer un ID unique
        chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(time.time())

        # Envoyer le premier chunk (role)
        first_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": ""},
                "finish_reason": None,
            }],
        }
        yield f"data: {json.dumps(first_chunk)}\n\n"

        # Streamer la réponse
        try:
            for chunk in self.agent.chat_sync(user_message):
                data = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": chunk},
                        "finish_reason": None,
                    }],
                }
                yield f"data: {json.dumps(data)}\n\n"

        except Exception as e:
            error_chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"\n\n[Erreur: {e}]"},
                    "finish_reason": "error",
                }],
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

        # Envoyer le chunk final
        final_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }],
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    def chat_sync(self, request: ChatRequest) -> ChatResponse:
        """
        Chat synchrone (non-streaming).

        Returns une réponse complète.
        """
        # Configurer le modèle
        self.agent.config.model = request.model

        # Extraire le dernier message utilisateur
        user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        # Collecter la réponse
        response_chunks = []
        for chunk in self.agent.chat_sync(user_message):
            response_chunks.append(chunk)

        full_response = "".join(response_chunks)
        stats = self.agent.get_stats()

        return ChatResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=full_response),
                    finish_reason="stop",
                )
            ],
            usage=ChatUsage(
                prompt_tokens=stats["tokens"]["prompt"],
                completion_tokens=stats["tokens"]["completion"],
                total_tokens=stats["tokens"]["total"],
            ),
        )


# === FACTORY ===

def create_app() -> FastAPI:
    """
    Crée l'application FastAPI THÉRÈSE.

    Returns:
        Instance FastAPI configurée.
    """
    app = FastAPI(
        title="THÉRÈSE API",
        description="API compatible OpenAI propulsée par Mistral",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS pour permettre les appels depuis des extensions
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Instance du serveur
    server = ThereseHTTPServer()

    # === ROUTES ===

    @app.get("/")
    async def root():
        """Page d'accueil."""
        return {
            "name": "THÉRÈSE API",
            "version": "0.2.0",
            "description": "Assistant de code IA français propulsé par Mistral",
            "endpoints": {
                "chat": "/v1/chat/completions",
                "models": "/v1/models",
                "health": "/health",
            },
        }

    @app.get("/health")
    async def health():
        """Health check."""
        return {
            "status": "ok",
            "model": therese_config.model,
            "api_key_configured": bool(therese_config.api_key),
        }

    @app.get("/v1/models", response_model=ModelsResponse)
    async def list_models():
        """Liste les modèles disponibles."""
        return ModelsResponse(
            data=[
                ModelInfo(id=m["id"])
                for m in server.MODELS
            ]
        )

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatRequest):
        """
        Endpoint de chat compatible OpenAI.

        Supporte le streaming SSE et les réponses synchrones.
        """
        if request.stream:
            return StreamingResponse(
                server.stream_chat(request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            response = server.chat_sync(request)
            return JSONResponse(content=response.model_dump())

    @app.post("/v1/completions")
    async def completions(request: dict):
        """
        Endpoint legacy completions (redirige vers chat).
        """
        # Convertir en format chat
        prompt = request.get("prompt", "")
        chat_request = ChatRequest(
            model=request.get("model", "mistral-large-latest"),
            messages=[ChatMessage(role="user", content=prompt)],
            stream=request.get("stream", False),
        )

        if chat_request.stream:
            return StreamingResponse(
                server.stream_chat(chat_request),
                media_type="text/event-stream",
            )
        else:
            response = server.chat_sync(chat_request)
            return JSONResponse(content=response.model_dump())

    @app.post("/reset")
    async def reset_conversation():
        """Réinitialise la conversation."""
        server.reset_agent()
        return {"status": "ok", "message": "Conversation réinitialisée"}

    return app
