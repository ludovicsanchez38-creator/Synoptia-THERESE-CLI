"""Configuration de THERESE CLI."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ThereseConfig:
    """Configuration principale de THERESE."""

    # API Mistral
    api_key: str = field(default_factory=lambda: os.getenv("MISTRAL_API_KEY", ""))
    model: str = "mistral-large-latest"  # ou mistral-large-3-25-12

    # Contexte
    max_context_tokens: int = 128_000  # Mistral Large 3 = 256K, on garde de la marge
    max_output_tokens: int = 8_192

    # Mode
    mode: Literal["auto", "safe", "yolo"] = "auto"
    ultrathink: bool = False  # Mode raisonnement étendu

    # Répertoire de travail
    working_dir: Path = field(default_factory=Path.cwd)

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
