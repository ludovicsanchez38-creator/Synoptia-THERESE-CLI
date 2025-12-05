# THÉRÈSE CLI 🇫🇷

**Assistant de code IA français propulsé par Mistral AI**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Mistral-Large-orange" alt="Mistral AI">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
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

**THÉRÈSE** (Terminal Helper for Engineering, Research, Editing, Software & Execution) est un assistant de code en ligne de commande, 100% français, inspiré de Claude Code mais propulsé par **Mistral AI**.

## Pourquoi THÉRÈSE ?

| | THÉRÈSE | Claude Code |
|---|---------|-------------|
| **IA** | Mistral AI 🇫🇷 | Anthropic 🇺🇸 |
| **Langage** | Python | TypeScript |
| **Taille** | ~30 MB | ~200 MB |
| **Prix API** | €€ | €€€€ |
| **Open Source** | ✅ Oui | ❌ Non |
| **Souveraineté** | 🇫🇷 France | 🇺🇸 USA |

## Installation

### Prérequis
- Python 3.11+
- [UV](https://docs.astral.sh/uv/) (gestionnaire de packages ultra-rapide)

### Installation rapide

```bash
# Installer UV si nécessaire
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer THÉRÈSE globalement
uv tool install therese-cli

# Ou depuis les sources
git clone https://github.com/synoptia/therese-cli.git
cd therese-cli
uv tool install .
```

### Configuration

```bash
# Ajouter votre clé API Mistral
export MISTRAL_API_KEY="votre-clé-api"

# (Optionnel) Ajouter à ~/.zshrc ou ~/.bashrc pour persister
echo 'export MISTRAL_API_KEY="votre-clé-api"' >> ~/.zshrc
```

Obtenez une clé API sur [console.mistral.ai](https://console.mistral.ai/)

## Utilisation

```bash
# Lancer THÉRÈSE
therese

# Lancer dans un dossier spécifique
therese /chemin/vers/projet
```

### Commandes slash

| Commande | Description |
|----------|-------------|
| `/help` | Affiche l'aide |
| `/init` | Initialise un projet avec THERESE.md |
| `/clear` | Efface la conversation |
| `/reset` | Reset complet (conversation + mémoire) |
| `/tree` | Affiche l'arborescence du projet |
| `/tasks` | Affiche la liste des tâches |
| `/status` | Affiche le statut (modèle, mode, tokens) |
| `/model` | Change le modèle Mistral |
| `/mode` | Change le mode (auto/safe/yolo) |
| `/stats` | Statistiques de la session |

### Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Enter` | Envoyer le message |
| `Ctrl+J` | Nouvelle ligne |
| `↑` / `↓` | Historique des prompts |
| `Ctrl+C` | Quitter |
| `Ctrl+L` | Effacer l'écran |

### Modes d'approbation

- **`auto`** (défaut) : Confirmation pour les actions dangereuses uniquement
- **`safe`** : Confirmation pour toutes les modifications
- **`yolo`** : Aucune confirmation (à vos risques !)

## Fonctionnalités

### 18 outils intégrés

**Fichiers**
- `read_file` - Lire un fichier
- `write_file` - Écrire un fichier
- `edit_file` - Éditer un fichier (rechercher/remplacer)
- `glob` - Rechercher des fichiers par pattern
- `grep` - Rechercher du texte dans les fichiers
- `tree` - Afficher l'arborescence
- `diff` / `diff_preview` - Comparer des fichiers

**Shell & Git**
- `bash` - Exécuter des commandes shell
- `git` - Commandes git
- `git_commit` - Créer un commit
- `git_status` - Statut du repo

**Web**
- `web_fetch` - Récupérer une page web
- `web_search` - Recherche DuckDuckGo

**Projet**
- `project_detect` - Détecter le type de projet
- `project_run` - Lancer le projet

**Tâches**
- `task_list` / `task_add` / `task_update` - Gérer les tâches

### Support multi-modal (Vision)

THÉRÈSE supporte l'analyse d'images via Mistral Vision (Pixtral) :

```bash
# Coller le chemin d'une image dans l'input
/Users/vous/image.png Qu'est-ce qu'il y a sur cette image ?
```

### Messages de réflexion

25 messages humoristiques français pendant que THÉRÈSE réfléchit :
- "Fait cuire une baguette..."
- "Affine le camembert..."
- "Prépare le saucisson..."
- etc.

### Thème Bleu Blanc Rouge

- **TH** : Bleu (#0055A4)
- **ERE** : Blanc (#FFFFFF)
- **SE** : Rouge (#EF4135)
- **CLI** : Orange Mistral (#FF7000)

## Architecture

```
src/therese/
├── __init__.py
├── __main__.py          # Entry point CLI
├── agent.py             # Agent Mistral avec function calling
├── commands.py          # 12 commandes slash
├── config.py            # Configuration
├── memory.py            # Système de mémoire THERESE.md
├── tools/               # 18 outils
│   ├── base.py          # Classe de base Tool
│   ├── file.py          # read, write, edit
│   ├── search.py        # glob, grep
│   ├── shell.py         # bash
│   ├── git.py           # git, commit, status
│   ├── web.py           # fetch, search
│   └── ...
└── ui/
    ├── app.py           # Application Textual
    └── theme.py         # CSS Textual
```

## Stack technique

| Technologie | Rôle | Pourquoi |
|-------------|------|----------|
| **Python 3.11+** | Runtime | Écosystème IA mature, SDK Mistral prioritaire |
| **UV** | Package manager | 10-100x plus rapide que pip (écrit en Rust) |
| **Mistral AI** | LLM | Souveraineté FR, function calling robuste, 2-3x moins cher |
| **Textual** | UI terminal | CSS natif, streaming Markdown O(1) |
| **Rich** | Formatage | Markdown, syntax highlighting |

## Développement

```bash
# Cloner le repo
git clone https://github.com/synoptia/therese-cli.git
cd therese-cli

# Installer les dépendances
uv sync

# Lancer en mode dev
uv run therese

# Réinstaller après modifications
uv tool uninstall therese-cli && uv tool install .

# Nettoyer le cache UV si besoin
uv cache clean
```

## Roadmap

- [x] Agent Mistral avec function calling
- [x] 18 outils (fichiers, shell, git, web)
- [x] Streaming Markdown optimisé
- [x] Support images (Mistral Vision)
- [x] Historique de prompts (flèches ↑↓)
- [x] Barre de statut live (temps + tokens)
- [ ] Mode local avec Ollama
- [ ] MCP (Model Context Protocol)
- [ ] Plugins/extensions
- [ ] Checkpoints/rewind

## Contribuer

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

1. Fork le projet
2. Créer une branche (`git checkout -b feature/ma-feature`)
3. Commit (`git commit -m 'feat: ma feature'`)
4. Push (`git push origin feature/ma-feature`)
5. Ouvrir une Pull Request

## Licence

MIT License - voir [LICENSE](LICENSE)

## Crédits

Créé avec ❤️ par [Synoptia](https://synoptia.fr)

Propulsé par [Mistral AI](https://mistral.ai) 🇫🇷

---

<p align="center">
  <strong>THÉRÈSE</strong> - L'IA française qui code avec vous 🐓
</p>
