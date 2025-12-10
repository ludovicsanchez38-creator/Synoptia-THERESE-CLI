# THERESE CLI 0.3.0

**Assistant de code IA francais propulse par Mistral AI**

<p align="center">
  <img src="https://img.shields.io/badge/Version-0.3.0-blue" alt="Version 0.3.0">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Mistral-Large_3-orange" alt="Mistral AI">
  <img src="https://img.shields.io/badge/License-Apache_2.0-blue" alt="Apache 2.0 License">
  <img src="https://img.shields.io/badge/Made_in-France-red" alt="Made in France">
</p>

```
 ████████╗██╗  ██╗███████╗██████╗ ███████╗███████╗███████╗     ██████╗██╗     ██╗
 ╚══██╔══╝██║  ██║██╔════╝██╔══██╗██╔════╝██╔════╝██╔════╝    ██╔════╝██║     ██║
    ██║   ███████║█████╗  ██████╔╝█████╗  ███████╗█████╗      ██║     ██║     ██║
    ██║   ██╔══██║██╔══╝  ██╔══██╗██╔══╝  ╚════██║██╔══╝      ██║     ██║     ██║
    ██║   ██║  ██║███████╗██║  ██║███████╗███████║███████╗    ╚██████╗███████╗██║
    ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝     ╚═════╝╚══════╝╚═╝
```

---

**THERESE** (Terminal Helper for Engineering, Research, Editing, Software & Execution) est un assistant de code en ligne de commande, 100% francais, inspire de Claude Code mais propulse par **Mistral AI**.

## Nouveautes v0.3.0

- **Checkpoints/Rewind** - Sauvegarde automatique avant modifications, restauration en un clic
- **Background Tasks** - Executez des commandes longues en arriere-plan (`/bg`, `/jobs`, `/kill`)
- **Sub-Agents** - Deleguer des taches a des agents specialises (code-reviewer, debugger, planner)
- **Ctrl+R Historique** - Recherche fuzzy dans l'historique des prompts
- **Double Esc** - Quick rewind vers le dernier checkpoint
- **21 commandes slash** et **21 outils** disponibles

## Pourquoi THERESE ?

| | THERESE | Claude Code |
|---|---------|-------------|
| **IA** | Mistral AI | Anthropic |
| **Langage** | Python | TypeScript |
| **Taille** | ~30 MB | ~200 MB |
| **Prix API** | Economique | Premium |
| **Open Source** | Oui | Non |
| **Souverainete** | France | USA |

## Installation

### Prerequis
- Python 3.11+
- [UV](https://docs.astral.sh/uv/) (gestionnaire de packages ultra-rapide)

### Installation rapide

```bash
# Installer UV si necessaire
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer THERESE globalement
uv tool install therese-cli

# Ou depuis les sources
git clone https://github.com/ludovicsanchez38-creator/Synoptia-THERESE-CLI.git
cd Synoptia-THERESE-CLI
uv tool install .
```

### Configuration

```bash
# Ajouter votre cle API Mistral
export MISTRAL_API_KEY="votre-cle-api"

# (Optionnel) Ajouter a ~/.zshrc ou ~/.bashrc pour persister
echo 'export MISTRAL_API_KEY="votre-cle-api"' >> ~/.zshrc
```

Obtenez une cle API sur [console.mistral.ai](https://console.mistral.ai/)

## Utilisation

```bash
# Lancer THERESE
therese

# Lancer dans un dossier specifique
therese /chemin/vers/projet

# Mode headless (une commande)
therese -p "Explique ce code"

# Utiliser un agent specifique
therese -a code-reviewer "Revise ce fichier"
```

## 21 Commandes Slash

### Commandes de base
| Commande | Description |
|----------|-------------|
| `/help` | Affiche l'aide |
| `/clear` | Efface l'ecran |
| `/reset` | Reinitialise la conversation |
| `/compact` | Compresse et resume la conversation |
| `/status` | Affiche le statut (modele, tokens, cout) |
| `/cost` | Cout estime de la session |
| `/export` | Exporte la conversation en Markdown |

### Projet et memoire
| Commande | Description |
|----------|-------------|
| `/init` | Initialise THERESE.md pour le projet |
| `/tree` | Affiche l'arborescence du projet |
| `/tasks` | Affiche la liste des taches |
| `/memory` | Affiche/gere la memoire projet |

### Configuration
| Commande | Description |
|----------|-------------|
| `/model` | Change le modele Mistral |
| `/mode` | Change le mode (auto/safe/yolo) |
| `/provider` | Change le provider (mistral/ollama) |

### Checkpoints (nouveau v0.3.0)
| Commande | Description |
|----------|-------------|
| `/checkpoint [name]` | Cree un checkpoint nomme |
| `/checkpoints` | Liste tous les checkpoints |
| `/rewind [id]` | Restaure un checkpoint |

### Background Tasks (nouveau v0.3.0)
| Commande | Description |
|----------|-------------|
| `/bg <command>` | Lance une commande en arriere-plan |
| `/jobs` | Liste les taches en cours |
| `/kill <id>` | Arrete une tache |
| `/output <id>` | Affiche l'output d'une tache |

## Raccourcis Clavier

| Raccourci | Action |
|-----------|--------|
| `Enter` | Envoyer le message |
| `Ctrl+J` | Nouvelle ligne |
| `Haut/Bas` | Historique des prompts |
| `Ctrl+R` | Recherche dans l'historique |
| `Ctrl+L` | Effacer l'ecran |
| `Ctrl+T` | Afficher l'arborescence |
| `Ctrl+G` | Git status |
| `Double Esc` | Quick rewind |
| `Ctrl+C` | Quitter |

## 21 Outils Integres

### Fichiers
- `read_file` - Lire un fichier
- `write_file` - Ecrire un fichier
- `edit_file` - Editer (rechercher/remplacer)
- `glob` - Rechercher par pattern
- `grep` - Rechercher du texte

### Systeme
- `bash` - Executer des commandes shell
- `tree` - Afficher l'arborescence

### Git
- `git` - Commandes git generiques
- `git_commit` - Creer un commit
- `git_status` - Statut du repo

### Web
- `web_fetch` - Recuperer une page web
- `web_search` - Recherche DuckDuckGo

### Projet
- `project_detect` - Detecter le type de projet
- `project_run` - Lancer le projet

### Diff
- `diff` - Comparer des fichiers
- `diff_preview` - Previsualiser les changements

### Taches
- `task_list` - Lister les taches
- `task_add` - Ajouter une tache
- `task_update` - Mettre a jour une tache

### Agents (nouveau v0.3.0)
- `spawn_subagent` - Deleguer a un agent specialise
- `list_agents` - Lister les agents disponibles

## Agents Integres

| Agent | Description | Modele |
|-------|-------------|--------|
| `code-reviewer` | Expert revue de code (bugs, perf, secu) | codestral-latest |
| `debugger` | Expert debogage et analyse d'erreurs | mistral-large-latest |
| `planner` | Architecte pour planifier les implementations | mistral-large-latest |

```bash
# Utiliser un agent
therese -a code-reviewer "Revise src/main.py"
therese -a debugger "Analyse cette erreur: ..."
therese -a planner "Planifie l'ajout d'une feature X"
```

## Modes d'Approbation

- **`auto`** (defaut) : Confirmation pour les actions dangereuses uniquement
- **`safe`** : Confirmation pour toutes les modifications
- **`yolo`** : Aucune confirmation (a vos risques !)

## Modeles Disponibles

### Mistral API (defaut)
| Modele | Usage | Prix |
|--------|-------|------|
| `mistral-large-latest` | General, creatif (defaut) | $2/$6 |
| `devstral-2512` | Code, 72% SWE-bench | Gratuit |
| `codestral-latest` | Code specialise | $0.3/$0.9 |
| `magistral-medium-latest` | Raisonnement | $2/$5 |

### Ollama (local, experimental)
```bash
therese --provider ollama --model ministral-3:14b
```

## Architecture

```
src/therese/
├── __init__.py          # Version 0.3.0
├── __main__.py          # Entry point CLI
├── cli.py               # CLI Click avec sous-commandes
├── agent.py             # Agent Mistral avec function calling
├── commands.py          # 21 commandes slash
├── config.py            # Configuration
├── memory.py            # Systeme de memoire THERESE.md
├── background.py        # [NEW] Background tasks manager
├── tools/               # 21 outils
│   ├── base.py          # Classe de base Tool
│   ├── read.py, write.py, edit.py
│   ├── bash.py, tree.py
│   ├── git.py           # git, commit, status
│   ├── web.py           # fetch, search
│   ├── diff.py          # diff, preview
│   ├── project.py       # detect, run
│   ├── task.py          # list, add, update
│   └── subagent.py      # [NEW] spawn, list
├── providers/           # [NEW] Abstraction providers
│   ├── base.py          # ProviderBase ABC
│   ├── mistral.py       # MistralProvider
│   └── ollama.py        # OllamaProvider
├── checkpoints/         # [NEW] Sauvegarde/restauration
│   ├── manager.py       # CheckpointManager
│   └── storage.py       # Git/File storage
├── agents/              # Agents YAML
│   └── builtin/         # code-reviewer, debugger, planner
├── ui/
│   ├── app.py           # Application Textual
│   └── theme.py         # CSS Textual
├── shell/               # Shell Assistant
├── http/                # HTTP Server (therese serve)
├── mcp/                 # Model Context Protocol
└── sessions/            # Multi-sessions SQLite
```

## Stack Technique

| Technologie | Role | Pourquoi |
|-------------|------|----------|
| **Python 3.11+** | Runtime | Ecosysteme IA mature, SDK Mistral prioritaire |
| **UV** | Package manager | 10-100x plus rapide que pip (ecrit en Rust) |
| **Mistral AI** | LLM | Souverainete FR, function calling robuste |
| **Textual** | UI terminal | CSS natif, streaming Markdown O(1) |
| **Rich** | Formatage | Markdown, syntax highlighting |

## Developpement

```bash
# Cloner le repo
git clone https://github.com/ludovicsanchez38-creator/Synoptia-THERESE-CLI.git
cd Synoptia-THERESE-CLI

# Installer les dependances
uv sync

# Lancer en mode dev
uv run therese

# Reinstaller apres modifications
uv tool uninstall therese-cli && uv cache clean && uv tool install .
```

## Roadmap

- [x] Agent Mistral avec function calling
- [x] 21 outils (fichiers, shell, git, web, taches, agents)
- [x] 21 commandes slash
- [x] Streaming Markdown optimise
- [x] Support images (Mistral Vision)
- [x] Historique de prompts (fleches)
- [x] Ctrl+R recherche historique
- [x] Checkpoints/rewind
- [x] Background tasks
- [x] Sub-agents
- [x] MCP (Model Context Protocol)
- [ ] Provider Ollama (stable)
- [ ] Plugins/extensions

## Contribuer

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

1. Fork le projet
2. Creer une branche (`git checkout -b feature/ma-feature`)
3. Commit (`git commit -m 'feat: ma feature'`)
4. Push (`git push origin feature/ma-feature`)
5. Ouvrir une Pull Request

## Licence

Apache License 2.0 - voir [LICENSE](LICENSE)

## Credits

Cree avec par [Synoptia](https://synoptia.fr)

Propulse par [Mistral AI](https://mistral.ai)

---

<p align="center">
  <strong>THERESE</strong> - L'IA francaise qui code avec vous
</p>
