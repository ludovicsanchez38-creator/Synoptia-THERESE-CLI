"""
Gestionnaire de sessions THÉRÈSE.

Stockage SQLite des conversations pour reprise et historique.
Inspiré de OpenCode qui permet multi-session et shareable links.
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Session:
    """Une session de conversation."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[dict] = field(default_factory=list)
    project_path: str = ""
    model: str = "mistral-large-latest"
    tokens_used: int = 0
    metadata: dict = field(default_factory=dict)

    @classmethod
    def create(cls, title: str = "", project_path: str = "") -> "Session":
        """Crée une nouvelle session."""
        now = datetime.now()
        return cls(
            id=uuid.uuid4().hex[:8],
            title=title or f"Session {now:%Y-%m-%d %H:%M}",
            created_at=now,
            updated_at=now,
            project_path=project_path or str(Path.cwd()),
        )

    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Ajoute un message à la session."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        })
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Convertit en dictionnaire."""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": self.messages,
            "project_path": self.project_path,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Crée depuis un dictionnaire."""
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=data.get("messages", []),
            project_path=data.get("project_path", ""),
            model=data.get("model", "mistral-large-latest"),
            tokens_used=data.get("tokens_used", 0),
            metadata=data.get("metadata", {}),
        )

    def to_markdown(self) -> str:
        """Exporte la session en Markdown."""
        lines = [
            f"# {self.title}",
            "",
            f"**ID:** {self.id}",
            f"**Créée:** {self.created_at:%Y-%m-%d %H:%M}",
            f"**Mise à jour:** {self.updated_at:%Y-%m-%d %H:%M}",
            f"**Projet:** {self.project_path}",
            f"**Modèle:** {self.model}",
            f"**Tokens:** {self.tokens_used:,}",
            "",
            "---",
            "",
        ]

        for msg in self.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            if role == "user":
                lines.append(f"## 👤 Utilisateur")
            elif role == "assistant":
                lines.append(f"## 🤖 THÉRÈSE")
            elif role == "system":
                lines.append(f"## ⚙️ Système")
            else:
                lines.append(f"## {role}")

            if timestamp:
                lines.append(f"*{timestamp}*")

            lines.append("")
            lines.append(content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)


class SessionManager:
    """
    Gestionnaire de sessions avec stockage SQLite.

    Permet de sauvegarder, charger, lister et supprimer des sessions.
    """

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else Path.home() / ".therese" / "sessions.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialise la base de données."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                messages TEXT NOT NULL,
                project_path TEXT,
                model TEXT,
                tokens_used INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_updated_at ON sessions(updated_at DESC)
        """)
        conn.commit()
        conn.close()

    def save(self, session: Session) -> None:
        """Sauvegarde une session."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO sessions
            (id, title, created_at, updated_at, messages, project_path, model, tokens_used, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.id,
            session.title,
            session.created_at.isoformat(),
            session.updated_at.isoformat(),
            json.dumps(session.messages, ensure_ascii=False),
            session.project_path,
            session.model,
            session.tokens_used,
            json.dumps(session.metadata, ensure_ascii=False),
        ))
        conn.commit()
        conn.close()

    def load(self, session_id: str) -> Session | None:
        """Charge une session par ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return Session(
            id=row[0],
            title=row[1],
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            messages=json.loads(row[4]),
            project_path=row[5] or "",
            model=row[6] or "mistral-large-latest",
            tokens_used=row[7] or 0,
            metadata=json.loads(row[8]) if row[8] else {},
        )

    def load_latest(self) -> Session | None:
        """Charge la dernière session modifiée."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id FROM sessions ORDER BY updated_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self.load(row[0])

    def list_all(self, limit: int = 50) -> list[dict]:
        """Liste toutes les sessions (résumé)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT id, title, created_at, updated_at, project_path, model, tokens_used
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "title": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "project_path": row[4],
                "model": row[5],
                "tokens_used": row[6],
            }
            for row in rows
        ]

    def delete(self, session_id: str) -> bool:
        """Supprime une session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,)
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Recherche dans les sessions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT id, title, updated_at
            FROM sessions
            WHERE title LIKE ? OR messages LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        rows = cursor.fetchall()
        conn.close()

        return [
            {"id": row[0], "title": row[1], "updated_at": row[2]}
            for row in rows
        ]

    def export_markdown(self, session_id: str, output_path: Path | str | None = None) -> str | None:
        """
        Exporte une session en Markdown.

        Args:
            session_id: ID de la session
            output_path: Chemin de sortie (optionnel)

        Returns:
            Contenu Markdown ou None si session non trouvée
        """
        session = self.load(session_id)
        if not session:
            return None

        markdown = session.to_markdown()

        if output_path:
            output_path = Path(output_path)
            output_path.write_text(markdown, encoding="utf-8")

        return markdown

    def stats(self) -> dict:
        """Retourne les statistiques globales."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(tokens_used) as total_tokens,
                MIN(created_at) as first_session,
                MAX(updated_at) as last_activity
            FROM sessions
        """)
        row = cursor.fetchone()
        conn.close()

        return {
            "total_sessions": row[0] or 0,
            "total_tokens": row[1] or 0,
            "first_session": row[2],
            "last_activity": row[3],
        }


# Instance globale (lazy)
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Retourne l'instance globale du SessionManager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
