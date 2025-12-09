"""
Gestion des sessions pour THÉRÈSE.

Permet de sauvegarder, reprendre et partager des conversations.

Fonctionnalités :
- Sauvegarde automatique en SQLite
- Reprise de session (--session ID ou --continue)
- Export en Markdown
- Shareable links (future)

Storage: ~/.therese/sessions.db
"""

from .manager import SessionManager, Session

__all__ = ["SessionManager", "Session"]
