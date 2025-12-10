"""
Ollama Provider.

Provider pour les modèles locaux via Ollama.
Focus sur les modèles Mistral : ministral-3, devstral, codestral.
"""

import json
from typing import Iterator

import httpx

from .base import ProviderBase, StreamChunk


class OllamaProvider(ProviderBase):
    """Provider pour Ollama (modèles locaux)."""

    name = "ollama"
    supports_tools = True  # Ollama supporte tools depuis v0.4
    supports_vision = True  # Via modèles comme llava, pixtral

    # Modèles Mistral recommandés pour Mac M4 16GB
    RECOMMENDED_MODELS = {
        "fast": "ministral-3:3b",      # 3GB - Ultra rapide
        "balanced": "ministral-3:8b",   # 6GB - Sweet spot
        "capable": "ministral-3:14b",   # 9GB - Plus capable
        "code": "devstral:24b",         # 14GB - Agent code (limite RAM)
        "code_legacy": "codestral:22b", # 13GB - Code spécialisé
    }

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self._available_models: list[str] | None = None

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        json_data: dict | None = None,
        stream: bool = False,
        timeout: float | None = None,
    ):
        """Fait une requête HTTP à Ollama."""
        url = f"{self.base_url}{endpoint}"

        if stream:
            return httpx.stream(
                method,
                url,
                json=json_data,
                timeout=timeout,
            )
        else:
            response = httpx.request(
                method,
                url,
                json=json_data,
                timeout=timeout or 30.0,
            )
            response.raise_for_status()
            return response.json()

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """Convertit les messages au format Ollama."""
        result = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            images = msg.get("images", [])

            ollama_msg = {"role": role, "content": content}

            # Images en base64 pour Ollama
            if images:
                ollama_images = []
                for img in images:
                    if isinstance(img, dict) and "base64" in img:
                        ollama_images.append(img["base64"])
                    elif isinstance(img, str) and img.startswith("data:"):
                        # Extraire le base64 de data:image/...;base64,...
                        base64_part = img.split(",", 1)[-1]
                        ollama_images.append(base64_part)
                if ollama_images:
                    ollama_msg["images"] = ollama_images

            result.append(ollama_msg)
        return result

    def _convert_tools(self, tools: list[dict] | None) -> list[dict] | None:
        """Convertit les tools au format Ollama."""
        if not tools:
            return None

        # Ollama utilise un format similaire à OpenAI
        ollama_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                ollama_tools.append({
                    "type": "function",
                    "function": tool.get("function", {}),
                })
            else:
                ollama_tools.append(tool)
        return ollama_tools

    def chat_stream(
        self,
        messages: list[dict],
        model: str,
        tools: list[dict] | None = None,
    ) -> Iterator[StreamChunk]:
        """Streaming synchrone via l'API Ollama."""
        ollama_messages = self._convert_messages(messages)

        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
        }

        # Ajouter tools si supportés
        if tools:
            ollama_tools = self._convert_tools(tools)
            if ollama_tools:
                payload["tools"] = ollama_tools

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=None,  # Pas de timeout pour le streaming
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    chunk = StreamChunk()

                    # Message content
                    message = data.get("message", {})
                    if message.get("content"):
                        chunk.content = message["content"]

                    # Tool calls
                    if message.get("tool_calls"):
                        chunk.tool_calls = message["tool_calls"]

                    # Done + stats
                    if data.get("done"):
                        chunk.finish_reason = "stop"
                        # Ollama retourne les stats à la fin
                        if "prompt_eval_count" in data:
                            chunk.usage = {
                                "prompt_tokens": data.get("prompt_eval_count", 0),
                                "completion_tokens": data.get("eval_count", 0),
                            }

                    if chunk.content or chunk.tool_calls or chunk.finish_reason:
                        yield chunk

        except httpx.ConnectError:
            yield StreamChunk(
                content="[Erreur] Ollama non accessible. Lancez `ollama serve` ou vérifiez l'URL.",
                finish_reason="error",
            )
        except httpx.HTTPStatusError as e:
            # Pour streaming, on doit lire le contenu avant d'y accéder
            try:
                error_text = e.response.read().decode("utf-8", errors="replace")
            except Exception:
                error_text = str(e)
            yield StreamChunk(
                content=f"[Erreur HTTP] {e.response.status_code}: {error_text}",
                finish_reason="error",
            )

    def list_models(self) -> list[str]:
        """Liste les modèles installés sur Ollama."""
        if self._available_models is not None:
            return self._available_models

        try:
            data = self._make_request("/api/tags")
            models = [m["name"] for m in data.get("models", [])]
            self._available_models = models
            return models
        except Exception:
            return []

    def is_available(self) -> bool:
        """Vérifie si Ollama est accessible."""
        try:
            self._make_request("/api/tags", timeout=5.0)
            return True
        except Exception:
            return False

    def get_default_model(self) -> str:
        """Modèle par défaut : ministral-3:8b si disponible."""
        models = self.list_models()

        # Préférence : ministral-3:8b > devstral > codestral > premier dispo
        for preferred in ["ministral-3:8b", "devstral:24b", "codestral:22b"]:
            if preferred in models:
                return preferred

        return models[0] if models else "ministral-3:8b"

    def pull_model(self, model: str) -> Iterator[str]:
        """Télécharge un modèle depuis Ollama."""
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=None,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        status = data.get("status", "")
                        if "pulling" in status or "downloading" in status:
                            completed = data.get("completed", 0)
                            total = data.get("total", 1)
                            pct = int(completed / total * 100) if total else 0
                            yield f"{status}: {pct}%"
                        else:
                            yield status
        except Exception as e:
            yield f"Erreur: {e}"

    def get_recommended_model(self, use_case: str = "balanced") -> str:
        """Retourne le modèle recommandé pour un cas d'usage."""
        return self.RECOMMENDED_MODELS.get(use_case, "ministral-3:8b")
