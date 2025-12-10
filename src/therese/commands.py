"""
Commandes slash pour THERESE CLI.

/help, /clear, /reset, /compact, /init, /cost, /memory, etc.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Coroutine, Any

from .memory import get_memory_manager
from .tools.project import detect_project


@dataclass
class SlashCommand:
    """Une commande slash."""

    name: str
    description: str
    usage: str
    handler: Callable[..., Coroutine[Any, Any, str]]


class CommandRegistry:
    """Registre des commandes slash."""

    def __init__(self):
        self._commands: dict[str, SlashCommand] = {}
        self._register_builtin_commands()

    def register(self, command: SlashCommand) -> None:
        """Enregistre une commande."""
        self._commands[command.name] = command

    def get(self, name: str) -> SlashCommand | None:
        """Récupère une commande."""
        return self._commands.get(name.lstrip("/"))

    def list_all(self) -> list[SlashCommand]:
        """Liste toutes les commandes."""
        return list(self._commands.values())

    def _register_builtin_commands(self) -> None:
        """Enregistre les commandes intégrées."""
        self.register(SlashCommand(
            name="help",
            description="Affiche l'aide",
            usage="/help [commande]",
            handler=self._cmd_help,
        ))

        self.register(SlashCommand(
            name="clear",
            description="Efface l'écran",
            usage="/clear",
            handler=self._cmd_clear,
        ))

        self.register(SlashCommand(
            name="reset",
            description="Réinitialise la conversation",
            usage="/reset",
            handler=self._cmd_reset,
        ))

        self.register(SlashCommand(
            name="compact",
            description="Résume et compacte la conversation",
            usage="/compact",
            handler=self._cmd_compact,
        ))

        self.register(SlashCommand(
            name="init",
            description="Initialise THERESE pour le projet",
            usage="/init",
            handler=self._cmd_init,
        ))

        self.register(SlashCommand(
            name="cost",
            description="Affiche le coût de la session",
            usage="/cost",
            handler=self._cmd_cost,
        ))

        self.register(SlashCommand(
            name="memory",
            description="Affiche/modifie la mémoire projet",
            usage="/memory [show|add|clear]",
            handler=self._cmd_memory,
        ))

        self.register(SlashCommand(
            name="model",
            description="Change le modèle",
            usage="/model [mistral-large-latest|codestral-latest|...]",
            handler=self._cmd_model,
        ))

        self.register(SlashCommand(
            name="mode",
            description="Change le mode d'approbation",
            usage="/mode [auto|safe|yolo]",
            handler=self._cmd_mode,
        ))

        self.register(SlashCommand(
            name="tasks",
            description="Affiche les tâches en cours",
            usage="/tasks",
            handler=self._cmd_tasks,
        ))

        self.register(SlashCommand(
            name="tree",
            description="Affiche l'arborescence du projet",
            usage="/tree [depth]",
            handler=self._cmd_tree,
        ))

        self.register(SlashCommand(
            name="status",
            description="Affiche le statut Git",
            usage="/status",
            handler=self._cmd_status,
        ))

        self.register(SlashCommand(
            name="export",
            description="Exporte la conversation en Markdown",
            usage="/export [filename]",
            handler=self._cmd_export,
        ))

        self.register(SlashCommand(
            name="provider",
            description="Change le provider LLM (mistral/ollama)",
            usage="/provider [mistral|ollama]",
            handler=self._cmd_provider,
        ))

        self.register(SlashCommand(
            name="checkpoint",
            description="Crée un checkpoint nommé",
            usage="/checkpoint [name]",
            handler=self._cmd_checkpoint,
        ))

        self.register(SlashCommand(
            name="rewind",
            description="Restaure un checkpoint",
            usage="/rewind [id]",
            handler=self._cmd_rewind,
        ))

        self.register(SlashCommand(
            name="checkpoints",
            description="Liste les checkpoints",
            usage="/checkpoints",
            handler=self._cmd_checkpoints,
        ))

        self.register(SlashCommand(
            name="bg",
            description="Lance une commande en arrière-plan",
            usage="/bg <command>",
            handler=self._cmd_bg,
        ))

        self.register(SlashCommand(
            name="jobs",
            description="Liste les tâches en arrière-plan",
            usage="/jobs",
            handler=self._cmd_jobs,
        ))

        self.register(SlashCommand(
            name="kill",
            description="Arrête une tâche en arrière-plan",
            usage="/kill <task_id>",
            handler=self._cmd_kill,
        ))

        self.register(SlashCommand(
            name="output",
            description="Affiche l'output d'une tâche",
            usage="/output <task_id>",
            handler=self._cmd_output,
        ))

    async def _cmd_help(self, args: str = "") -> str:
        """Affiche l'aide."""
        if args:
            cmd = self.get(args)
            if cmd:
                return f"""## /{cmd.name}

**Description:** {cmd.description}
**Usage:** `{cmd.usage}`
"""
            return f"Commande inconnue: {args}"

        lines = [
            "# 📚 Commandes THÉRÈSE",
            "",
            "| Commande | Description |",
            "|----------|-------------|",
        ]

        for cmd in sorted(self._commands.values(), key=lambda c: c.name):
            lines.append(f"| `/{cmd.name}` | {cmd.description} |")

        lines.extend([
            "",
            "## Raccourcis clavier",
            "- `Ctrl+C` : Quitter",
            "- `Ctrl+L` : Effacer l'écran",
            "- `Ctrl+R` : Réinitialiser",
            "- `Escape` : Annuler",
        ])

        return "\n".join(lines)

    async def _cmd_clear(self, args: str = "") -> str:
        """Efface l'écran."""
        return "__CLEAR__"

    async def _cmd_reset(self, args: str = "") -> str:
        """Réinitialise la conversation."""
        return "__RESET__"

    async def _cmd_compact(self, args: str = "") -> str:
        """Compacte la conversation."""
        return "__COMPACT__"

    async def _cmd_init(self, args: str = "") -> str:
        """Initialise THERESE pour le projet."""
        path = Path.cwd()
        info = detect_project(path)
        memory = get_memory_manager(path)

        # Mettre à jour la mémoire
        memory.update_from_detection(info.to_dict())

        lines = [
            "# 🎉 Projet initialisé !",
            "",
            f"**Projet:** {info.name}",
            f"**Type:** {info.type}",
            f"**Langage:** {info.language}",
            f"**Package Manager:** {info.package_manager}",
        ]

        if info.frameworks:
            lines.append(f"**Frameworks:** {', '.join(info.frameworks)}")

        lines.extend([
            "",
            f"📄 Fichier `THERESE.md` créé dans `{path}`",
            "",
            "Je suis prête à travailler sur ce projet !",
        ])

        return "\n".join(lines)

    async def _cmd_cost(self, args: str = "") -> str:
        """Affiche le coût."""
        # TODO: Implémenter le tracking de tokens
        return """# 💰 Coût de la session

| Métrique | Valeur |
|----------|--------|
| Tokens envoyés | ~ |
| Tokens reçus | ~ |
| Coût estimé | ~ |

*Tracking détaillé à venir dans une prochaine version.*
"""

    async def _cmd_memory(self, args: str = "") -> str:
        """Gère la mémoire."""
        memory = get_memory_manager()

        if args == "clear":
            memory._memory = None
            if memory.memory_file.exists():
                memory.memory_file.unlink()
            return "✅ Mémoire effacée"

        if args.startswith("add "):
            item = args[4:].strip()
            if item.startswith("pattern:"):
                memory.add_pattern(item[8:].strip())
                return f"✅ Pattern ajouté: {item[8:].strip()}"
            elif item.startswith("gotcha:"):
                memory.add_gotcha(item[7:].strip())
                return f"✅ Piège ajouté: {item[7:].strip()}"
            elif item.startswith("file:"):
                memory.add_key_file(item[5:].strip())
                return f"✅ Fichier clé ajouté: {item[5:].strip()}"

        return memory.memory.to_markdown()

    async def _cmd_model(self, args: str = "") -> str:
        """Change le modèle."""
        from .config import config

        # Si provider Ollama, utiliser les modèles locaux
        if config.provider == "ollama":
            return await self._cmd_model_ollama(args)

        # Modèles Mistral API organisés par catégorie
        models = {
            "chat": [
                ("mistral-large-latest", "Flagship - meilleur qualité"),
                ("mistral-medium-latest", "Équilibré qualité/coût"),
                ("mistral-small-latest", "Rapide et économique"),
            ],
            "code": [
                ("devstral-2512", "72% SWE-bench, flagship - GRATUIT"),
                ("devstral-small-latest", "68% SWE-bench, économique"),
                ("codestral-latest", "Spécialisé code"),
            ],
            "vision": [
                ("pixtral-large-latest", "Multimodal - analyse d'images"),
                ("pixtral-12b-2409", "Vision léger"),
            ],
            "reasoning": [
                ("magistral-medium-latest", "🧠 Raisonnement frontier"),
                ("magistral-small-latest", "🧠 Raisonnement efficient"),
            ],
        }

        all_models = []
        for category_models in models.values():
            all_models.extend([m[0] for m in category_models])

        if not args:
            lines = ["# 🤖 Modèles Mistral API", ""]

            for category, category_models in models.items():
                if not category_models:
                    continue
                lines.append(f"**{category.upper()}**")
                for m, desc in category_models:
                    marker = "→" if m == config.model else " "
                    lines.append(f"{marker} `{m}` - {desc}")
                lines.append("")

            lines.append(f"**Actuel:** `{config.model}`")
            lines.append("")
            lines.append("Usage: `/model mistral-large-latest`")
            return "\n".join(lines)

        if args in all_models:
            config.model = args
            return f"✅ Modèle changé: `{args}`"

        # Suggestions si le modèle est proche
        suggestions = [m for m in all_models if args.lower() in m.lower()]
        if suggestions:
            return f"❌ Modèle inconnu: `{args}`\n\n**Suggestions:** {', '.join(f'`{s}`' for s in suggestions)}"

        return f"❌ Modèle inconnu: `{args}`\n\nTape `/model` pour voir la liste."

    async def _cmd_model_ollama(self, args: str = "") -> str:
        """Change le modèle Ollama."""
        from .config import config
        from .providers import OllamaProvider

        provider = OllamaProvider(base_url=config.ollama_base_url)

        if not provider.is_available():
            return "❌ Ollama n'est pas démarré.\n\nLance `ollama serve` dans un terminal."

        available_models = provider.list_models()

        if not args:
            lines = ["# 🦙 Modèles Ollama locaux", ""]

            if not available_models:
                lines.append("Aucun modèle installé.")
                lines.append("")
                lines.append("Installe un modèle: `ollama pull ministral-3:14b`")
            else:
                for m in available_models:
                    marker = "→" if m == config.ollama_model else " "
                    lines.append(f"{marker} `{m}`")

                lines.append("")
                lines.append(f"**Actuel:** `{config.ollama_model}`")
                lines.append("")
                lines.append("Usage: `/model ministral-3:14b`")

            return "\n".join(lines)

        # Vérifier si le modèle existe
        if args in available_models:
            config.ollama_model = args
            return f"✅ Modèle Ollama changé: `{args}`"

        # Suggestions
        suggestions = [m for m in available_models if args.lower() in m.lower()]
        if suggestions:
            return f"❌ Modèle inconnu: `{args}`\n\n**Disponibles:** {', '.join(f'`{s}`' for s in suggestions)}"

        return f"❌ Modèle inconnu: `{args}`\n\nTape `/model` pour voir les modèles installés."

    async def _cmd_mode(self, args: str = "") -> str:
        """Change le mode d'approbation."""
        from .config import config

        modes = {
            "auto": "Confirmation pour les actions potentiellement dangereuses",
            "safe": "Confirmation pour toutes les modifications de fichiers",
            "yolo": "Aucune confirmation (à vos risques et périls)",
        }

        if not args:
            lines = ["# 🔐 Modes d'approbation", ""]
            for m, desc in modes.items():
                marker = "→" if m == config.mode else " "
                lines.append(f"{marker} `{m}`: {desc}")
            lines.append("")
            lines.append(f"**Actuel:** `{config.mode}`")
            return "\n".join(lines)

        if args in modes:
            config.mode = args  # type: ignore
            return f"✅ Mode changé: `{args}`"

        return f"❌ Mode inconnu: {args}. Options: auto, safe, yolo"

    async def _cmd_tasks(self, args: str = "") -> str:
        """Affiche les tâches."""
        from .tools.task import task_manager
        return task_manager.to_markdown()

    async def _cmd_tree(self, args: str = "") -> str:
        """Affiche l'arborescence."""
        from .tools.tree import TreeTool

        depth = int(args) if args.isdigit() else 3
        tool = TreeTool()
        result = await tool.execute(max_depth=depth)
        return result.output

    async def _cmd_status(self, args: str = "") -> str:
        """Affiche le statut Git."""
        from .tools.git import GitStatusTool

        tool = GitStatusTool()
        result = await tool.execute()
        return result.output

    async def _cmd_export(self, args: str = "") -> str:
        """Exporte la conversation en Markdown."""
        from datetime import datetime

        # Générer le nom de fichier par défaut
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = args.strip() if args else f"therese_export_{timestamp}.md"

        # S'assurer que l'extension est .md
        if not filename.endswith(".md"):
            filename += ".md"

        # Retourner une commande spéciale pour que l'UI gère l'export
        return f"__EXPORT__:{filename}"

    async def _cmd_provider(self, args: str = "") -> str:
        """Change le provider LLM."""
        from .config import config

        providers = {
            "mistral": "API Mistral Cloud (devstral-2, mistral-large, etc.)",
            "ollama": "Modèles locaux via Ollama (ministral-3, devstral, codestral)",
        }

        if not args:
            lines = ["# 🔌 Providers disponibles", ""]
            for p, desc in providers.items():
                marker = "→" if p == config.provider else " "
                lines.append(f"{marker} `{p}`: {desc}")
            lines.append("")
            lines.append(f"**Actuel:** `{config.provider}`")

            if config.provider == "ollama":
                lines.append(f"**URL:** `{config.ollama_base_url}`")
                lines.append(f"**Modèle:** `{config.ollama_model}`")
            else:
                lines.append(f"**Modèle:** `{config.model}`")

            lines.append("")
            lines.append("Usage: `/provider mistral` ou `/provider ollama`")

            # Lister modèles Ollama si disponible
            if config.provider == "ollama":
                try:
                    from .providers import OllamaProvider
                    ollama = OllamaProvider(base_url=config.ollama_base_url)
                    models = ollama.list_models()
                    if models:
                        lines.append("")
                        lines.append("**Modèles Ollama installés:**")
                        for m in models[:10]:
                            lines.append(f"  - `{m}`")
                except Exception:
                    pass

            return "\n".join(lines)

        if args in providers:
            old_provider = config.provider
            config.provider = args  # type: ignore

            if args == "ollama":
                # Vérifier si Ollama est accessible
                try:
                    from .providers import OllamaProvider
                    ollama = OllamaProvider(base_url=config.ollama_base_url)
                    if not ollama.is_available():
                        config.provider = old_provider  # type: ignore
                        return f"❌ Ollama non accessible à `{config.ollama_base_url}`\n\nLancez `ollama serve` d'abord."

                    models = ollama.list_models()
                    model_info = f"\nModèles disponibles: {', '.join(models[:5])}" if models else ""
                    return f"✅ Provider changé: `{args}`\nModèle actif: `{config.ollama_model}`{model_info}"
                except Exception as e:
                    config.provider = old_provider  # type: ignore
                    return f"❌ Erreur Ollama: {e}"

            return f"✅ Provider changé: `{args}`\nModèle actif: `{config.model}`"

        return f"❌ Provider inconnu: `{args}`\n\nOptions: mistral, ollama"

    async def _cmd_checkpoint(self, args: str = "") -> str:
        """Crée un checkpoint nommé."""
        from .checkpoints import CheckpointManager

        manager = CheckpointManager(Path.cwd())
        name = args.strip() if args else None

        checkpoint = manager.create(name=name, is_auto=False)
        if checkpoint:
            return f"Checkpoint créé: `{checkpoint.id}` ({checkpoint.name})"

        return "Aucune modification à sauvegarder."

    async def _cmd_rewind(self, args: str = "") -> str:
        """Restaure un checkpoint."""
        from .checkpoints import CheckpointManager

        manager = CheckpointManager(Path.cwd())

        if args.strip():
            # Restaurer un checkpoint spécifique
            checkpoint_id = args.strip()
            success = manager.restore(checkpoint_id)
            if success:
                return f"Checkpoint `{checkpoint_id}` restauré."
            return f"Checkpoint `{checkpoint_id}` non trouvé."

        # Quick rewind (dernier checkpoint)
        success, message = manager.rewind()
        return message

    async def _cmd_checkpoints(self, args: str = "") -> str:
        """Liste les checkpoints."""
        from .checkpoints import CheckpointManager

        manager = CheckpointManager(Path.cwd())
        return manager.to_markdown()

    async def _cmd_bg(self, args: str = "") -> str:
        """Lance une commande en arrière-plan."""
        from .background import get_background_manager

        if not args.strip():
            return "Usage: `/bg <command>`\n\nExemple: `/bg npm install`"

        manager = get_background_manager()
        success, message = await manager.run(
            args.strip(),
            working_dir=str(Path.cwd()),
        )
        return f"{''+'' if success else ''} {message}"

    async def _cmd_jobs(self, args: str = "") -> str:
        """Liste les tâches en arrière-plan."""
        from .background import get_background_manager

        manager = get_background_manager()
        return manager.to_markdown()

    async def _cmd_kill(self, args: str = "") -> str:
        """Arrête une tâche en arrière-plan."""
        from .background import get_background_manager

        if not args.strip():
            return "Usage: `/kill <task_id>`"

        manager = get_background_manager()
        success, message = manager.kill(args.strip())
        return message

    async def _cmd_output(self, args: str = "") -> str:
        """Affiche l'output d'une tâche."""
        from .background import get_background_manager

        if not args.strip():
            return "Usage: `/output <task_id>`"

        parts = args.strip().split()
        task_id = parts[0]
        tail = int(parts[1]) if len(parts) > 1 else 50

        manager = get_background_manager()
        task = manager.get_task(task_id)

        if not task:
            return f"Tâche `{task_id}` non trouvée"

        output = manager.get_output(task_id, tail=tail)

        return f"""# Output: `{task_id}`

**Commande:** `{task.command}`
**Statut:** {task.status.value}
**Durée:** {task._get_duration()}

```
{output}
```"""


# Instance globale
commands = CommandRegistry()


async def process_slash_command(input_text: str) -> tuple[bool, str]:
    """
    Traite une commande slash.

    Returns:
        (is_command, response): True si c'était une commande, avec la réponse
    """
    if not input_text.startswith("/"):
        return False, ""

    parts = input_text[1:].split(maxsplit=1)
    cmd_name = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    command = commands.get(cmd_name)
    if not command:
        return True, f"❌ Commande inconnue: /{cmd_name}\n\nTapez `/help` pour voir les commandes disponibles."

    response = await command.handler(args)
    return True, response
