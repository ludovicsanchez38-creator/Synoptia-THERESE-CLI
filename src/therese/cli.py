"""
Point d'entrée CLI pour THERESE.

Usage:
    therese [OPTIONS] [PROMPT]
    therese "Explique-moi ce code"
    therese --model mistral-large-3-25-12

Mode Headless:
    echo "Explique ce code" | therese
    cat error.log | therese --fix
    therese "Crée un test" --headless
    therese --fix --exit-code=1 "npm install"
"""

# IMPORTANT: Appliquer nest_asyncio AVANT tout import async
# Résout "Event loop is closed" avec httpx/Mistral SDK
# SAUF pour "serve" qui utilise uvicorn (conflit event loop)
import sys
if "serve" not in sys.argv:
    import nest_asyncio
    nest_asyncio.apply()

import os
from pathlib import Path

import click
from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown

from . import __version__
from .config import Colors, config

console = Console(stderr=True)  # Output sur stderr pour headless


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


def run_headless(
    prompt: str | None,
    stdin_data: str | None,
    fix_mode: bool = False,
    exit_code: int | None = None,
    output_format: str = "text",
    agent_name: str | None = None,
) -> int:
    """
    Exécute THÉRÈSE en mode headless (sans UI).

    Args:
        prompt: Le prompt utilisateur
        stdin_data: Données lues depuis stdin
        fix_mode: Si True, analyse une erreur et propose un fix
        exit_code: Code d'erreur de la commande échouée (pour --fix)
        output_format: Format de sortie (text, json, markdown)
        agent_name: Nom de l'agent personnalisé à utiliser

    Returns:
        Code de sortie (0 = succès)
    """
    from .agent import ThereseAgent

    # Charger l'agent personnalisé si spécifié
    agent_config = None
    if agent_name:
        from .agents import load_agent
        agent_config = load_agent(agent_name)
        if not agent_config:
            console.print(f"[red]Erreur:[/] Agent '{agent_name}' non trouvé", style="red")
            console.print("[dim]Utilisez 'therese agents list' pour voir les agents disponibles[/]")
            return 1
        console.print(f"{agent_config.icon} [bold]{agent_config.name}[/]", style="dim")

    # Construire le prompt final
    if fix_mode:
        if exit_code is not None and prompt:
            # Mode fix avec commande et exit code
            full_prompt = f"""La commande suivante a échoué avec le code {exit_code}:

```bash
{prompt}
```

{f"Output/Erreur:{chr(10)}```{chr(10)}{stdin_data[:3000] if stdin_data else 'Pas de sortie'}{chr(10)}```" if stdin_data else ""}

Analyse l'erreur et propose une commande corrigée.
Réponds UNIQUEMENT avec la commande corrigée, sans explication ni bloc de code."""
        elif stdin_data:
            # Mode fix avec juste stdin (ex: cat error.log | therese --fix)
            full_prompt = f"""Analyse cette erreur/log et propose une solution:

```
{stdin_data[:4000]}
```

Propose une commande ou solution pour résoudre ce problème.
Sois concis et direct."""
        else:
            console.print("[red]Erreur:[/] --fix nécessite un stdin ou une commande", style="red")
            return 1
    else:
        # Mode normal
        if stdin_data and prompt:
            full_prompt = f"{stdin_data}\n\n{prompt}"
        elif stdin_data:
            full_prompt = stdin_data
        elif prompt:
            full_prompt = prompt
        else:
            console.print("[red]Erreur:[/] Aucun prompt fourni", style="red")
            return 1

    # Créer l'agent et exécuter
    agent = ThereseAgent()

    # Appliquer la config de l'agent personnalisé
    if agent_config:
        # Override le modèle si spécifié
        if agent_config.model:
            agent.config.model = agent_config.model

        # Prepend le system prompt de l'agent
        if agent_config.system_prompt:
            # Injecter le system prompt de l'agent avant le premier message
            original_system = agent.messages[0].content if agent.messages else ""
            agent.messages[0].content = f"{agent_config.system_prompt}\n\n---\n\n{original_system}"

    try:
        # Streaming sur stderr (stdout réservé pour output parsable)
        output_chunks = []

        for chunk in agent.chat_sync(full_prompt):
            output_chunks.append(chunk)
            # Streamer sur stderr
            sys.stderr.write(chunk)
            sys.stderr.flush()

        sys.stderr.write("\n")

        # Si format JSON demandé, output structuré sur stdout
        if output_format == "json":
            import json
            result = {
                "response": "".join(output_chunks),
                "tokens": agent.get_stats()["tokens"],
                "model": agent.config.model,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))

        return 0

    except KeyboardInterrupt:
        sys.stderr.write("\n[Interrompu]\n")
        return 130
    except Exception as e:
        sys.stderr.write(f"\n[Erreur: {e}]\n")
        return 1


@click.group(invoke_without_command=True)
@click.pass_context
@click.option(
    "--prompt", "-p",
    default=None,
    help="Prompt à envoyer (mode headless)",
)
@click.option(
    "--model", "-m",
    default=None,
    help="Modèle à utiliser (défaut: devstral-2 pour API, ministral-3:8b pour Ollama)",
)
@click.option(
    "--provider", "-P",
    type=click.Choice(["mistral", "ollama"]),
    default="mistral",
    help="Provider LLM: mistral (API cloud) ou ollama (local)",
)
@click.option(
    "--ollama-url",
    default="http://localhost:11434",
    help="URL du serveur Ollama (si --provider ollama)",
)
@click.option(
    "--working-dir", "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Répertoire de travail",
)
@click.option(
    "--doubledose", "-D",
    is_flag=True,
    help="Active le mode DOUBLEDOSE (raisonnement étendu à la française)",
)
@click.option(
    "--version", "-v",
    is_flag=True,
    help="Affiche la version",
)
@click.option(
    "--headless", "-H",
    is_flag=True,
    help="Mode sans interface (output sur stderr)",
)
@click.option(
    "--one-shot", "-1",
    is_flag=True,
    help="Une seule réponse puis exit (alias pour --headless)",
)
@click.option(
    "--fix", "-f",
    is_flag=True,
    help="Analyse une erreur et propose un fix",
)
@click.option(
    "--exit-code", "-e",
    type=int,
    default=None,
    help="Code de sortie de la commande échouée (avec --fix)",
)
@click.option(
    "--output", "-o",
    type=click.Choice(["text", "json", "markdown"]),
    default="text",
    help="Format de sortie (headless)",
)
@click.option(
    "--agent", "-a",
    default=None,
    help="Utiliser un agent personnalisé (ex: code-reviewer, debugger, planner)",
)
def main(
    ctx: click.Context,
    prompt: str | None,
    model: str | None,
    provider: str,
    ollama_url: str,
    working_dir: Path | None,
    doubledose: bool,
    version: bool,
    headless: bool,
    one_shot: bool,
    fix: bool,
    exit_code: int | None,
    output: str,
    agent: str | None,
) -> None:
    """
    THÉRÈSE CLI - Assistant de code IA français.

    Propulsé par Mistral 3 🇫🇷

    \b
    Exemples:
        therese                              # Lance l'interface interactive
        therese -p "Explique ce fichier"     # Requête headless
        therese -H -p "Bonjour"              # Mode headless explicite
        echo "code" | therese                # Pipe stdin
        cat error.log | therese --fix        # Analyse et corrige erreur
        therese -a code-reviewer "Review main.py"  # Utiliser un agent

    \b
    Sous-commandes:
        therese on                       # Active le shell assistant
        therese off                      # Désactive le shell assistant
        therese serve                    # Lance le serveur HTTP
        therese agents list              # Liste des agents disponibles
        therese agents show <nom>        # Détails d'un agent
        therese hook-status              # Statut des hooks
        therese mcp-list                 # Liste des serveurs MCP
        therese sessions                 # Liste des sessions
    """
    # Si une sous-commande est appelée, ne pas exécuter main
    if ctx.invoked_subcommand is not None:
        return

    if version:
        console.print(f"THÉRÈSE CLI v{__version__}")
        return

    # Configuration provider
    config.provider = provider  # type: ignore
    config.ollama_base_url = ollama_url

    # Configuration modèle (défaut selon provider si non spécifié)
    if model:
        if provider == "ollama":
            config.ollama_model = model
        else:
            config.model = model
    # Sinon garde les défauts: devstral-2 (mistral) ou ministral-3:8b (ollama)

    if working_dir:
        config.working_dir = working_dir
    config.ultrathink = doubledose  # DOUBLEDOSE = ultrathink à la française 🇫🇷

    # Vérifier la clé API (seulement pour provider mistral)
    if provider == "mistral" and not config.api_key:
        console.print(
            "[bold red]Erreur:[/] Variable MISTRAL_API_KEY non définie.\n\n"
            "Exportez votre clé API Mistral :\n"
            "  export MISTRAL_API_KEY=votre_clé\n\n"
            "Ou utilisez le provider Ollama (local) :\n"
            "  therese --provider ollama\n\n"
            "Ou créez un fichier .env dans le répertoire courant.",
            style="red",
        )
        sys.exit(1)

    # Vérifier Ollama si provider ollama
    if provider == "ollama":
        from .providers import OllamaProvider
        ollama = OllamaProvider(base_url=ollama_url)
        if not ollama.is_available():
            console.print(
                f"[bold red]Erreur:[/] Ollama non accessible à {ollama_url}\n\n"
                "Lancez Ollama :\n"
                "  ollama serve\n\n"
                "Ou vérifiez l'URL avec --ollama-url",
                style="red",
            )
            sys.exit(1)
        # Afficher info provider
        console.print(f"[dim]Provider: Ollama ({ollama_url})[/]")
        console.print(f"[dim]Modèle: {config.ollama_model}[/]")

    # Détecter si stdin a des données (pipe)
    stdin_data = None
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()

    # Mode headless automatique si:
    # - --headless ou --one-shot explicite
    # - --fix mode
    # - stdin pipe (ex: echo "..." | therese)
    # - --prompt fourni
    # - --agent spécifié
    is_headless = headless or one_shot or fix or stdin_data or prompt or agent

    if is_headless:
        # Mode headless
        exit_status = run_headless(
            prompt=prompt,
            stdin_data=stdin_data,
            fix_mode=fix,
            exit_code=exit_code,
            output_format=output,
            agent_name=agent,
        )
        sys.exit(exit_status)

    # Mode interactif avec Textual
    from .ui import ThereseApp

    app = ThereseApp(working_dir=working_dir or config.working_dir)
    app.run()


# === SOUS-COMMANDES ===

@main.command()
def on():
    """Active le shell assistant pour la session courante."""
    console.print(Text.assemble(
        ("✓ ", "green"),
        ("THÉRÈSE Shell Assistant ", f"bold {Colors.ORANGE}"),
        ("activé", "green"),
    ))
    console.print()
    console.print("[dim]Les erreurs de commandes seront analysées automatiquement.[/]")
    console.print("[dim]Pour désactiver: [bold]therese off[/] ou [bold]toff[/][/]")
    console.print()
    console.print("[yellow]Note:[/] Pour une activation permanente, utilisez:")
    console.print("  [bold]therese install-hook[/]")


@main.command()
def off():
    """Désactive le shell assistant."""
    console.print(Text.assemble(
        ("✗ ", "yellow"),
        ("THÉRÈSE Shell Assistant ", f"bold {Colors.ORANGE}"),
        ("désactivé", "yellow"),
    ))


@main.command("install-hook")
@click.option("--shell", "-s", type=click.Choice(["zsh", "bash"]), default=None,
              help="Shell cible (auto-détecté si non spécifié)")
def install_hook(shell: str | None):
    """Installe le hook shell assistant dans .zshrc/.bashrc."""
    from .shell import ShellHookManager

    manager = ShellHookManager()

    if shell is None:
        shell = manager.detect_shell()
        console.print(f"[dim]Shell détecté: {shell}[/]")

    console.print(f"\n[bold]Installation du hook THÉRÈSE pour {shell}...[/]\n")
    manager.install(shell)


@main.command("uninstall-hook")
@click.option("--shell", "-s", type=click.Choice(["zsh", "bash"]), default=None,
              help="Shell cible (auto-détecté si non spécifié)")
def uninstall_hook(shell: str | None):
    """Désinstalle le hook shell assistant."""
    from .shell import ShellHookManager

    manager = ShellHookManager()

    if shell is None:
        shell = manager.detect_shell()

    console.print(f"\n[bold]Désinstallation du hook THÉRÈSE pour {shell}...[/]\n")
    manager.uninstall(shell)


@main.command("hook-status")
def hook_status():
    """Affiche le statut d'installation des hooks."""
    from .shell import ShellHookManager

    manager = ShellHookManager()
    status = manager.status()

    console.print("\n[bold]Statut des hooks THÉRÈSE Shell Assistant[/]\n")
    console.print(f"  Shell actuel: [bold]{status['current_shell']}[/]")
    console.print()

    for shell in ["zsh", "bash"]:
        info = status[shell]
        installed = "[green]✓ installé[/]" if info["installed"] else "[dim]✗ non installé[/]"
        console.print(f"  {shell}: {installed}")
        console.print(f"       [dim]{info['rc_file']}[/]")


@main.command()
@click.option("--port", "-p", default=3000, help="Port du serveur")
@click.option("--host", default="127.0.0.1", help="Host du serveur")
def serve(port: int, host: str):
    """Lance le serveur HTTP API (compatible OpenAI)."""
    console.print(f"\n[bold {Colors.ORANGE}]Serveur THÉRÈSE[/] démarré\n")
    console.print(f"  URL:  http://{host}:{port}")
    console.print(f"  API:  http://{host}:{port}/v1/chat/completions")
    console.print(f"  Docs: http://{host}:{port}/docs")
    console.print("\n[dim]Ctrl+C pour arrêter[/]")

    # Lancer le serveur FastAPI
    try:
        from .http import create_app
        import uvicorn
        app = create_app()
        uvicorn.run(app, host=host, port=port, log_level="info")
    except ImportError:
        console.print("\n[red]Erreur:[/] Module HTTP non disponible.")
        console.print("Installez les dépendances: [bold]pip install fastapi uvicorn[/]")
        sys.exit(1)


@main.command("mcp-list")
def mcp_list():
    """Liste les serveurs MCP configurés."""
    console.print("\n[bold]Serveurs MCP configurés[/]\n")

    config_path = Path.home() / ".therese" / "mcp.yaml"
    if not config_path.exists():
        console.print(f"  [dim]Aucun serveur configuré[/]")
        console.print(f"\n  Créez le fichier: [bold]{config_path}[/]")
        console.print("  Exemple de configuration:")
        console.print("""
  [dim]servers:
    github:
      transport: stdio
      command: npx
      args: ["-y", "@modelcontextprotocol/server-github"]
      env:
        GITHUB_TOKEN: "${{GITHUB_TOKEN}}"[/]
""")
        return

    try:
        import yaml
        with open(config_path) as f:
            mcp_config = yaml.safe_load(f)

        servers = mcp_config.get("servers", {})
        if not servers:
            console.print("  [dim]Aucun serveur configuré[/]")
            return

        for name, server in servers.items():
            transport = server.get("transport", "stdio")
            command = server.get("command", "?")
            console.print(f"  [bold]{name}[/] ({transport})")
            console.print(f"    [dim]{command}[/]")

    except Exception as e:
        console.print(f"  [red]Erreur lecture config: {e}[/]")


@main.command()
def sessions():
    """Liste les sessions sauvegardées."""
    console.print("\n[bold]Sessions sauvegardées[/]\n")

    db_path = Path.home() / ".therese" / "sessions.db"
    if not db_path.exists():
        console.print("  [dim]Aucune session sauvegardée[/]")
        return

    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT id, title, updated_at FROM sessions ORDER BY updated_at DESC LIMIT 10"
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            console.print("  [dim]Aucune session sauvegardée[/]")
            return

        for session_id, title, updated_at in rows:
            console.print(f"  [bold]{session_id}[/] - {title}")
            console.print(f"    [dim]{updated_at}[/]")

    except Exception as e:
        console.print(f"  [red]Erreur: {e}[/]")


# === COMMANDES AGENTS ===

@main.group()
def agents():
    """Gestion des agents personnalisés."""
    pass


@agents.command("list")
def agents_list():
    """Liste tous les agents disponibles."""
    from .agents import AgentLoader

    loader = AgentLoader()
    agent_list = loader.list_agents()

    console.print("\n[bold]Agents disponibles[/]\n")

    if not agent_list:
        console.print("  [dim]Aucun agent configuré[/]")
        console.print(f"\n  Créez un agent dans: [bold]~/.therese/agents/[/]")
        return

    # Trier: builtin puis user
    builtin = [a for a in agent_list if "builtin" in a.tags]
    user = [a for a in agent_list if "user" in a.tags]

    if builtin:
        console.print("  [dim]─── Intégrés ───[/]")
        for agent in builtin:
            console.print(f"  {agent.icon} [bold]{agent.name}[/]")
            console.print(f"      [dim]{agent.description}[/]")

    if user:
        console.print("\n  [dim]─── Personnalisés ───[/]")
        for agent in user:
            console.print(f"  {agent.icon} [bold]{agent.name}[/]")
            console.print(f"      [dim]{agent.description}[/]")

    console.print(f"\n  Usage: [bold]therese --agent <nom> \"prompt\"[/]")


@agents.command("show")
@click.argument("name")
def agents_show(name: str):
    """Affiche les détails d'un agent."""
    from .agents import AgentLoader

    loader = AgentLoader()
    agent = loader.get_agent(name)

    if not agent:
        console.print(f"[red]Agent '{name}' non trouvé[/]")
        return

    console.print(f"\n{agent.icon} [bold]{agent.name}[/] v{agent.version}\n")
    console.print(f"[dim]{agent.description}[/]\n")

    if agent.model:
        console.print(f"  Modèle: [bold]{agent.model}[/]")

    if agent.tools:
        console.print(f"  Outils: {', '.join(agent.tools)}")

    if agent.mcp_servers:
        console.print(f"  MCP: {', '.join(agent.mcp_servers)}")

    if agent.author:
        console.print(f"  Auteur: {agent.author}")

    console.print("\n[dim]─── System Prompt ───[/]")
    console.print(Markdown(agent.system_prompt[:1000]))


@agents.command("create")
@click.argument("name")
@click.option("--description", "-d", default="", help="Description de l'agent")
@click.option("--icon", "-i", default="🤖", help="Emoji icon")
def agents_create(name: str, description: str, icon: str):
    """Crée un nouvel agent personnalisé."""
    from .agents import AgentConfig, AgentLoader

    loader = AgentLoader()

    config = AgentConfig(
        name=name,
        description=description or f"Agent personnalisé: {name}",
        icon=icon,
        system_prompt=f"""Tu es {name}, un assistant spécialisé.

## Ton rôle
[Décris ici le rôle de l'agent]

## Format de réponse
[Décris le format attendu]

## Règles
- Règle 1
- Règle 2
""",
    )

    path = loader.create_agent(config)
    console.print(f"\n[green]✓[/] Agent créé: [bold]{path}[/]")
    console.print("\n  Éditez le fichier pour personnaliser le system_prompt.")


@agents.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="Êtes-vous sûr de vouloir supprimer cet agent?")
def agents_delete(name: str):
    """Supprime un agent personnalisé."""
    from .agents import AgentLoader

    loader = AgentLoader()

    if loader.delete_agent(name):
        console.print(f"[green]✓[/] Agent '{name}' supprimé")
    else:
        console.print(f"[red]Agent '{name}' non trouvé ou intégré (non supprimable)[/]")


if __name__ == "__main__":
    main()
