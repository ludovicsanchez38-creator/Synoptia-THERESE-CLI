"""Configuration de THERESE CLI."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()


def _get_default_working_dir() -> Path:
    """Retourne le répertoire de travail par défaut, le crée si besoin."""
    default = Path(os.getenv(
        "THERESE_WORKING_DIR",
        os.path.expanduser("~/Desktop/Therese repo")
    ))
    # Créer le dossier s'il n'existe pas
    if not default.exists():
        try:
            default.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Fallback sur le home si on ne peut pas créer
            default = Path.home()
    return default


@dataclass
class ThereseConfig:
    """Configuration principale de THERESE."""

    # API Mistral
    api_key: str = field(default_factory=lambda: os.getenv("MISTRAL_API_KEY", ""))
    model: str = "mistral-large-latest"  # ou mistral-large-3-25-12

    # Contexte
    max_context_tokens: int = 128_000  # Mistral Large 3 = 256K, on garde de la marge
    max_output_tokens: int = 8_192

    # Auto-compact
    auto_compact: bool = True  # Active le compactage automatique
    compact_threshold: float = 0.75  # Compacte à 75% du max_context_tokens
    compact_keep_recent: int = 10  # Garder les N derniers messages

    # Mode
    mode: Literal["auto", "safe", "yolo"] = "auto"
    ultrathink: bool = False  # Mode raisonnement étendu

    # Répertoire de travail (sandbox par défaut pour la sécurité)
    working_dir: Path = field(default_factory=_get_default_working_dir)

    # UI
    theme: Literal["mistral", "dark", "light"] = "mistral"

    # Fichiers à ignorer
    ignore_patterns: list[str] = field(default_factory=lambda: [
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        "*.pyc", "*.pyo", ".DS_Store", "*.egg-info", "dist", "build"
    ])

    def validate(self) -> None:
        """Valide la configuration."""
        if not self.api_key:
            raise ValueError(
                "MISTRAL_API_KEY non définie. "
                "Exportez-la ou créez un fichier .env"
            )


# Couleurs THERESE (Bleu Blanc Rouge + Orange Mistral)
class Colors:
    """Palette de couleurs THERESE."""

    # Drapeau français
    BLEU = "#0055A4"
    BLANC = "#FFFFFF"
    ROUGE = "#EF4135"

    # Mistral
    ORANGE = "#FF7000"
    ORANGE_LIGHT = "#FF9D4D"

    # UI
    BACKGROUND = "#0D1117"
    SURFACE = "#161B22"
    TEXT = "#E6EDF3"
    TEXT_DIM = "#7D8590"
    SUCCESS = "#3FB950"
    WARNING = "#D29922"
    ERROR = "#F85149"

    # Syntaxe
    KEYWORD = "#FF7B72"
    STRING = "#A5D6FF"
    COMMENT = "#8B949E"
    FUNCTION = "#D2A8FF"


# Configuration globale
config = ThereseConfig()
