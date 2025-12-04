"""
Point d'entrée CLI pour THERESE.

Usage:
    therese [OPTIONS] [PROMPT]
    therese "Explique-moi ce code"
    therese --model mistral-large-3-25-12
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.text import Text

from . import __version__
from .config import Colors, config

console = Console()


def print_banner() -> None:
    """Affiche la bannière THERESE."""
    banner = Text()

    # ASCII Art simplifié
    lines = [
        "╔════════════════════════════════════════════════════════╗",
        "║                                                        ║",
        "║   ████████╗██╗  ██╗███████╗██████╗ ███████╗███████╗   ║",
        "║   ╚══██╔══╝██║  ██║██╔════╝██╔══██╗██╔════╝██╔════╝   ║",
        "║      ██║   ███████║█████╗  ██████╔╝█████╗  ███████╗   ║",
        "║      ██║   ██╔══██║██╔══╝  ██╔══██╗██╔══╝  ╚════██║   ║",
        "║      ██║   ██║  ██║███████╗██║  ██║███████╗███████║   ║",
        "║      ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝   ║",
        "║                                                        ║",
        "╚════════════════════════════════════════════════════════╝",
    ]

    # Afficher avec dégradé bleu -> blanc -> rouge
    for i, line in enumerate(lines):
        if i < 4:
            color = Colors.BLEU
        elif i < 7:
            color = Colors.BLANC
        else:
            color = Colors.ROUGE
        banner.append(line + "\n", style=color)

    console.print(banner)

    # Sous-titre
    subtitle = Text()
    subtitle.append("                    CLI", style=f"bold {Colors.ORANGE}")
    subtitle.append(" │ ", style="dim")
    subtitle.append("Assistant IA français", style="dim")
    subtitle.append(" │ ", style="dim")
    subtitle.append("Mistral 3", style=f"{Colors.ORANGE}")
    subtitle.append(" 🇫🇷\n", style="")
    console.print(subtitle)


@click.command()
@click.argument("prompt", required=False, default=None)
@click.option(
    "--model", "-m",
    default="mistral-large-latest",
    help="Modèle Mistral à utiliser",
)
@click.option(
    "--working-dir", "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Répertoire de travail",
)
@click.option(
    "--ultrathink", "-u",
    is_flag=True,
    help="Active le mode ultrathink (raisonnement étendu)",
)
@click.option(
    "--version", "-v",
    is_flag=True,
    help="Affiche la version",
)
@click.option(
    "--no-ui",
    is_flag=True,
    help="Mode sans interface (une seule requête)",
)
def main(
    prompt: str | None,
    model: str,
    working_dir: Path | None,
    ultrathink: bool,
    version: bool,
    no_ui: bool,
) -> None:
    """
    THÉRÈSE CLI - Assistant de code IA français.

    Propulsé par Mistral 3 🇫🇷

    \b
    Exemples:
        therese                          # Lance l'interface interactive
        therese "Explique ce fichier"    # Requête unique
        therese -m mistral-large-3-25-12 # Utilise un modèle spécifique
    """
    if version:
        console.print(f"THÉRÈSE CLI v{__version__}")
        return

    # Configuration
    config.model = model
    if working_dir:
        config.working_dir = working_dir
    config.ultrathink = ultrathink

    # Vérifier la clé API
    if not config.api_key:
        console.print(
            "[bold red]Erreur:[/] Variable MISTRAL_API_KEY non définie.\n\n"
            "Exportez votre clé API Mistral :\n"
            "  export MISTRAL_API_KEY=votre_clé\n\n"
            "Ou créez un fichier .env dans le répertoire courant.",
            style="red",
        )
        sys.exit(1)

    # Mode non-interactif (une seule requête)
    if prompt and no_ui:
        import asyncio
        from .agent import ThereseAgent

        print_banner()
        agent = ThereseAgent()

        async def run_single():
            console.print(f"\n[bold {Colors.BLEU}]▶ Vous:[/] {prompt}\n")
            console.print(f"[bold {Colors.ORANGE}]◀ THÉRÈSE:[/]")

            async for chunk in agent.chat(prompt):
                console.print(chunk, end="")
            console.print()

        asyncio.run(run_single())
        return

    # Mode interactif avec Textual
    from .ui import ThereseApp

    app = ThereseApp(working_dir=working_dir or Path.cwd())

    # Si un prompt est fourni, on l'enverra au démarrage
    if prompt:
        # TODO: Envoyer le prompt initial
        pass

    app.run()


if __name__ == "__main__":
    main()
