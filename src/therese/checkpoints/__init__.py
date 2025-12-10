"""
Système de Checkpoints pour THERESE CLI.

Permet de sauvegarder et restaurer l'état du code :
- Auto-checkpoint avant chaque modification de fichier
- Checkpoints nommés manuels
- Rewind au dernier checkpoint
- Double Esc pour quick rewind

Inspiré de Claude Code checkpoints.
"""

from .manager import CheckpointManager, Checkpoint
from .storage import StorageBase, GitStashStorage, FileStorage

__all__ = [
    "CheckpointManager",
    "Checkpoint",
    "StorageBase",
    "GitStashStorage",
    "FileStorage",
]
