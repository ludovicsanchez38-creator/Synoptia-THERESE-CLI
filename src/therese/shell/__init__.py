"""
Shell Assistant pour THÉRÈSE CLI.

Fonctionnalités :
- Détection automatique des erreurs de commandes
- Proposition de corrections via Mistral
- Installation de hooks zsh/bash

Usage:
    therese on              # Active le shell assistant
    therese off             # Désactive
    therese install-hook    # Installe le hook permanent
"""

from .assistant import ShellAssistant
from .hooks import ShellHookManager

__all__ = ["ShellAssistant", "ShellHookManager"]
