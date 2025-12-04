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

        models = [
            "mistral-large-latest",
            "mistral-large-3-25-12",
            "codestral-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
        ]

        if not args:
            lines = ["# 🤖 Modèles disponibles", ""]
            for m in models:
                marker = "→" if m == config.model else " "
                lines.append(f"{marker} `{m}`")
            lines.append("")
            lines.append(f"**Actuel:** `{config.model}`")
            return "\n".join(lines)

        if args in models or args.startswith("mistral"):
            config.model = args
            return f"✅ Modèle changé: `{args}`"

        return f"❌ Modèle inconnu: {args}"

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
