"""
Mistral API Provider.

Provider pour l'API cloud Mistral AI.
Supporte : tools, vision (Pixtral), thinking (Magistral).
"""

from typing import Iterator
import os

from mistralai import Mistral
from mistralai.models import (
    AssistantMessage,
    ImageURLChunk,
    SystemMessage,
    TextChunk,
    ThinkChunk,
    ToolMessage,
    UserMessage,
)

from .base import ProviderBase, StreamChunk


class MistralProvider(ProviderBase):
    """Provider pour l'API Mistral AI."""

    name = "mistral"
    supports_tools = True
    supports_vision = True
    supports_thinking = True

    # Modèles disponibles par catégorie
    MODELS = {
        "code": [
            "devstral-2",
            "devstral-small-2",
            "codestral-latest",
        ],
        "chat": [
            "mistral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
        ],
        "vision": [
            "pixtral-large-latest",
            "pixtral-12b-2409",
        ],
        "reasoning": [
            "magistral-medium-2509",
            "magistral-small-2509",
        ],
    }

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY", "")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY non définie")

    def _create_client(self) -> Mistral:
        """Crée un nouveau client (pour thread safety)."""
        return Mistral(api_key=self.api_key)

    def _convert_messages(self, messages: list[dict]) -> list:
        """Convertit les messages au format Mistral."""
        result = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            images = msg.get("images", [])
            tool_calls = msg.get("tool_calls")
            tool_call_id = msg.get("tool_call_id")
            name = msg.get("name")

            if role == "system":
                result.append(SystemMessage(content=content))
            elif role == "user":
                if images:
                    # Multi-modal
                    chunks = []
                    if content:
                        chunks.append(TextChunk(text=content))
                    for img in images:
                        if isinstance(img, dict):
                            chunks.append(ImageURLChunk(image_url=img.get("url", "")))
                        else:
                            chunks.append(ImageURLChunk(image_url=img))
                    result.append(UserMessage(content=chunks))
                else:
                    result.append(UserMessage(content=content))
            elif role == "assistant":
                if tool_calls:
                    result.append(AssistantMessage(content=content or "", tool_calls=tool_calls))
                else:
                    result.append(AssistantMessage(content=content))
            elif role == "tool":
                result.append(ToolMessage(
                    content=content,
                    tool_call_id=tool_call_id,
                    name=name,
                ))
        return result

    def chat_stream(
        self,
        messages: list[dict],
        model: str,
        tools: list[dict] | None = None,
    ) -> Iterator[StreamChunk]:
        """Streaming synchrone via l'API Mistral."""
        client = self._create_client()
        mistral_messages = self._convert_messages(messages)

        # Appel streaming
        kwargs = {
            "model": model,
            "messages": mistral_messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = client.chat.stream(**kwargs)

        # Accumulateurs pour tool_calls
        current_tool_calls: list[dict] = []

        for event in response:
            if not event.data.choices:
                continue

            choice = event.data.choices[0]
            delta = choice.delta

            chunk = StreamChunk()

            # Contenu textuel
            if delta.content:
                if isinstance(delta.content, list):
                    text_parts = []
                    for item in delta.content:
                        if isinstance(item, ThinkChunk):
                            # Thinking visible (Magistral)
                            for think_text in item.thinking or []:
                                if hasattr(think_text, 'text') and think_text.text:
                                    text_parts.append(think_text.text)
                        elif hasattr(item, 'text') and item.text:
                            text_parts.append(item.text)
                    if text_parts:
                        chunk.content = "".join(text_parts)
                else:
                    chunk.content = delta.content

            # Tool calls
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    if tc.index >= len(current_tool_calls):
                        current_tool_calls.append({
                            "id": tc.id or "",
                            "type": "function",
                            "function": {
                                "name": tc.function.name or "",
                                "arguments": tc.function.arguments or "",
                            },
                        })
                    else:
                        if tc.function.arguments:
                            current_tool_calls[tc.index]["function"]["arguments"] += tc.function.arguments
                        if tc.function.name:
                            current_tool_calls[tc.index]["function"]["name"] = tc.function.name
                        if tc.id:
                            current_tool_calls[tc.index]["id"] = tc.id

            # Usage
            if event.data.usage:
                chunk.usage = {
                    "prompt_tokens": event.data.usage.prompt_tokens or 0,
                    "completion_tokens": event.data.usage.completion_tokens or 0,
                }

            # Finish reason
            if choice.finish_reason:
                chunk.finish_reason = choice.finish_reason
                if current_tool_calls:
                    chunk.tool_calls = current_tool_calls

            if chunk.content or chunk.tool_calls or chunk.usage:
                yield chunk

    def list_models(self) -> list[str]:
        """Liste tous les modèles Mistral disponibles."""
        all_models = []
        for category_models in self.MODELS.values():
            all_models.extend(category_models)
        return all_models

    def is_available(self) -> bool:
        """Vérifie si l'API Mistral est accessible."""
        try:
            client = self._create_client()
            # Simple check - list models
            return True
        except Exception:
            return False

    def get_default_model(self) -> str:
        """Modèle par défaut : devstral-2."""
        return "devstral-2"
