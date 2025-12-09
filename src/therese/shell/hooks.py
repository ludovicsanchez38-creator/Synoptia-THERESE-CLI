"""
Gestionnaire de hooks shell pour THÉRÈSE.

Permet d'installer des hooks dans zsh/bash qui détectent
automatiquement les erreurs de commandes et proposent des corrections.
"""

import os
import subprocess
from pathlib import Path
from typing import Literal

from rich.console import Console

console = Console(stderr=True)

ShellType = Literal["zsh", "bash"]


class ShellHookManager:
    """
    Gère l'installation et la désinstallation des hooks shell.

    Les hooks interceptent les commandes échouées et appellent
    THÉRÈSE pour proposer des corrections.
    """

    # Marqueurs pour identifier nos hooks dans les fichiers rc
    HOOK_START_MARKER = "# >>> THÉRÈSE Shell Assistant >>>"
    HOOK_END_MARKER = "# <<< THÉRÈSE Shell Assistant <<<"

    # Templates de hooks pour chaque shell
    ZSH_HOOK = '''
# >>> THÉRÈSE Shell Assistant >>>
# Installé automatiquement par `therese install-hook`
# Pour désinstaller: `therese uninstall-hook` ou supprimer ce bloc

_therese_last_cmd=""
_therese_enabled=true

# Capture la commande avant exécution
_therese_preexec() {
    _therese_last_cmd="$1"
}

# Vérifie le code de sortie après exécution
_therese_precmd() {
    local exit_code=$?

    # Ignorer si désactivé ou pas d'erreur
    [[ "$_therese_enabled" != "true" ]] && return
    [[ $exit_code -eq 0 ]] && return
    [[ -z "$_therese_last_cmd" ]] && return

    # Ignorer certaines commandes (éditeurs, pagers, etc.)
    case "$_therese_last_cmd" in
        vim*|nvim*|nano*|less*|more*|man*|cd\\ *|exit*|clear*)
            return
            ;;
    esac

    # Ignorer Ctrl+C (code 130)
    [[ $exit_code -eq 130 ]] && return

    # Proposer le fix via THÉRÈSE
    echo ""
    echo "\\033[0;33m💡 THÉRÈSE détecte une erreur (code $exit_code)\\033[0m"
    echo -n "   Analyser et corriger ? [o/N] "
    read -r response

    if [[ "$response" =~ ^[oOyY]$ ]]; then
        therese --fix --exit-code=$exit_code "$_therese_last_cmd"
    fi
}

# Fonctions pour activer/désactiver
therese_on() {
    _therese_enabled=true
    echo "\\033[0;32m✓ THÉRÈSE Shell Assistant activé\\033[0m"
}

therese_off() {
    _therese_enabled=false
    echo "\\033[0;33m✗ THÉRÈSE Shell Assistant désactivé\\033[0m"
}

# Installer les hooks
autoload -Uz add-zsh-hook 2>/dev/null || true
add-zsh-hook preexec _therese_preexec 2>/dev/null || true
add-zsh-hook precmd _therese_precmd 2>/dev/null || true

# Alias pratiques
alias ton="therese_on"
alias toff="therese_off"
alias tfix="therese --fix"
# <<< THÉRÈSE Shell Assistant <<<
'''

    BASH_HOOK = '''
# >>> THÉRÈSE Shell Assistant >>>
# Installé automatiquement par `therese install-hook`
# Pour désinstaller: `therese uninstall-hook` ou supprimer ce bloc

_therese_last_cmd=""
_therese_enabled=true

# Capture la commande via PROMPT_COMMAND
_therese_prompt_command() {
    local exit_code=$?

    # Ignorer si désactivé ou pas d'erreur
    [[ "$_therese_enabled" != "true" ]] && return
    [[ $exit_code -eq 0 ]] && return

    # Récupérer la dernière commande
    _therese_last_cmd=$(history 1 | sed 's/^[ ]*[0-9]*[ ]*//')

    [[ -z "$_therese_last_cmd" ]] && return

    # Ignorer certaines commandes
    case "$_therese_last_cmd" in
        vim*|nvim*|nano*|less*|more*|man*|cd\\ *|exit*|clear*)
            return
            ;;
    esac

    # Ignorer Ctrl+C (code 130)
    [[ $exit_code -eq 130 ]] && return

    # Proposer le fix via THÉRÈSE
    echo ""
    echo -e "\\033[0;33m💡 THÉRÈSE détecte une erreur (code $exit_code)\\033[0m"
    read -p "   Analyser et corriger ? [o/N] " response

    if [[ "$response" =~ ^[oOyY]$ ]]; then
        therese --fix --exit-code=$exit_code "$_therese_last_cmd"
    fi
}

# Fonctions pour activer/désactiver
therese_on() {
    _therese_enabled=true
    echo -e "\\033[0;32m✓ THÉRÈSE Shell Assistant activé\\033[0m"
}

therese_off() {
    _therese_enabled=false
    echo -e "\\033[0;33m✗ THÉRÈSE Shell Assistant désactivé\\033[0m"
}

# Installer le hook
if [[ ! "$PROMPT_COMMAND" =~ "_therese_prompt_command" ]]; then
    PROMPT_COMMAND="_therese_prompt_command${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
fi

# Alias pratiques
alias ton="therese_on"
alias toff="therese_off"
alias tfix="therese --fix"
# <<< THÉRÈSE Shell Assistant <<<
'''

    def __init__(self):
        self.home = Path.home()

    def detect_shell(self) -> ShellType:
        """Détecte le shell actuel."""
        shell = os.environ.get("SHELL", "/bin/zsh")
        if "zsh" in shell:
            return "zsh"
        elif "bash" in shell:
            return "bash"
        else:
            # Défaut à zsh sur macOS
            return "zsh"

    def get_rc_file(self, shell: ShellType) -> Path:
        """Retourne le chemin du fichier rc pour le shell."""
        if shell == "zsh":
            return self.home / ".zshrc"
        else:
            # Bash utilise .bashrc ou .bash_profile selon l'OS
            bashrc = self.home / ".bashrc"
            bash_profile = self.home / ".bash_profile"

            # Sur macOS, .bash_profile est préféré
            if bash_profile.exists():
                return bash_profile
            return bashrc

    def get_hook_script(self, shell: ShellType) -> str:
        """Retourne le script de hook pour le shell."""
        if shell == "zsh":
            return self.ZSH_HOOK
        else:
            return self.BASH_HOOK

    def is_installed(self, shell: ShellType | None = None) -> bool:
        """Vérifie si le hook est déjà installé."""
        shell = shell or self.detect_shell()
        rc_file = self.get_rc_file(shell)

        if not rc_file.exists():
            return False

        content = rc_file.read_text()
        return self.HOOK_START_MARKER in content

    def install(self, shell: ShellType | None = None) -> bool:
        """
        Installe le hook dans le fichier rc du shell.

        Returns:
            True si installé avec succès, False sinon.
        """
        shell = shell or self.detect_shell()
        rc_file = self.get_rc_file(shell)

        # Vérifier si déjà installé
        if self.is_installed(shell):
            console.print(f"[yellow]Hook déjà installé dans {rc_file}[/]")
            return True

        # Créer le fichier rc s'il n'existe pas
        if not rc_file.exists():
            rc_file.touch()

        # Ajouter le hook
        hook_script = self.get_hook_script(shell)

        try:
            with open(rc_file, "a") as f:
                f.write("\n")
                f.write(hook_script)
                f.write("\n")

            console.print(f"[green]✓ Hook installé dans {rc_file}[/]")
            console.print()
            console.print("[bold]Pour activer immédiatement:[/]")
            console.print(f"  source {rc_file}")
            console.print()
            console.print("[bold]Commandes disponibles:[/]")
            console.print("  [dim]ton[/]   - Activer THÉRÈSE Shell Assistant")
            console.print("  [dim]toff[/]  - Désactiver")
            console.print("  [dim]tfix[/]  - Analyser manuellement une erreur")

            return True

        except Exception as e:
            console.print(f"[red]Erreur lors de l'installation: {e}[/]")
            return False

    def uninstall(self, shell: ShellType | None = None) -> bool:
        """
        Désinstalle le hook du fichier rc.

        Returns:
            True si désinstallé avec succès, False sinon.
        """
        shell = shell or self.detect_shell()
        rc_file = self.get_rc_file(shell)

        if not rc_file.exists():
            console.print(f"[yellow]Fichier {rc_file} non trouvé[/]")
            return False

        if not self.is_installed(shell):
            console.print(f"[yellow]Hook non installé dans {rc_file}[/]")
            return True

        try:
            content = rc_file.read_text()

            # Trouver et supprimer le bloc de hook
            start_idx = content.find(self.HOOK_START_MARKER)
            end_idx = content.find(self.HOOK_END_MARKER)

            if start_idx == -1 or end_idx == -1:
                console.print("[red]Impossible de trouver les marqueurs du hook[/]")
                return False

            # Supprimer le bloc (inclure le marqueur de fin et le newline)
            end_idx = content.find("\n", end_idx) + 1
            new_content = content[:start_idx] + content[end_idx:]

            # Nettoyer les lignes vides multiples
            while "\n\n\n" in new_content:
                new_content = new_content.replace("\n\n\n", "\n\n")

            rc_file.write_text(new_content)

            console.print(f"[green]✓ Hook désinstallé de {rc_file}[/]")
            console.print()
            console.print("[bold]Pour appliquer immédiatement:[/]")
            console.print(f"  source {rc_file}")

            return True

        except Exception as e:
            console.print(f"[red]Erreur lors de la désinstallation: {e}[/]")
            return False

    def status(self) -> dict:
        """Retourne le statut d'installation pour tous les shells."""
        return {
            "zsh": {
                "installed": self.is_installed("zsh"),
                "rc_file": str(self.get_rc_file("zsh")),
            },
            "bash": {
                "installed": self.is_installed("bash"),
                "rc_file": str(self.get_rc_file("bash")),
            },
            "current_shell": self.detect_shell(),
        }


# Instance globale
hook_manager = ShellHookManager()
