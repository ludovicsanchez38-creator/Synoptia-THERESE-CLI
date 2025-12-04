# THÉRÈSE CLI 🇫🇷

```
████████╗██╗  ██╗███████╗██████╗ ███████╗███████╗███████╗
╚══██╔══╝██║  ██║██╔════╝██╔══██╗██╔════╝██╔════╝██╔════╝
   ██║   ███████║█████╗  ██████╔╝█████╗  ███████╗█████╗
   ██║   ██╔══██║██╔══╝  ██╔══██╗██╔══╝  ╚════██║██╔══╝
   ██║   ██║  ██║███████╗██║  ██║███████╗███████║███████╗
   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝
                         CLI
```

**Assistant de code IA français propulsé par Mistral 3**

THÉRÈSE CLI est un assistant de programmation en ligne de commande, inspiré de Claude Code et Codex CLI, mais propulsé par les modèles Mistral. 100% français, open-source, et conçu pour les développeurs.

## Caractéristiques

- 🇫🇷 **Français natif** - Conçu par et pour les développeurs francophones
- 🔥 **Mistral 3** - Propulsé par Mistral Large 3 (256K contexte)
- 🛠️ **Outils intégrés** - Lecture/écriture de fichiers, bash, recherche
- 🎨 **UI Terminal** - Interface Textual moderne et réactive
- 🔓 **Open Source** - Licence Apache 2.0

## Installation

```bash
# Avec UV (recommandé)
uv tool install therese-cli

# Avec pip
pip install therese-cli
```

## Configuration

Exportez votre clé API Mistral :

```bash
export MISTRAL_API_KEY=votre_cle_api
```

Ou créez un fichier `.env` :

```env
MISTRAL_API_KEY=votre_cle_api
```

## Utilisation

```bash
# Lancer l'interface interactive
therese

# Requête unique
therese "Explique ce fichier" --no-ui

# Spécifier un modèle
therese -m mistral-large-3-25-12

# Spécifier un répertoire de travail
therese -d /chemin/vers/projet
```

## Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Ctrl+C` | Quitter |
| `Ctrl+L` | Effacer l'écran |
| `Ctrl+R` | Réinitialiser la conversation |
| `Escape` | Annuler l'opération en cours |

## Outils disponibles

THÉRÈSE dispose de 6 outils pour interagir avec votre code :

| Outil | Description |
|-------|-------------|
| `read_file` | Lire le contenu d'un fichier |
| `write_file` | Écrire dans un fichier |
| `edit_file` | Modifier un fichier existant |
| `bash` | Exécuter des commandes shell |
| `glob` | Rechercher des fichiers par pattern |
| `grep` | Rechercher du texte dans les fichiers |

## Couleurs

L'interface utilise les couleurs symboliques :

- **THÉRÈSE** : Bleu (#0055A4), Blanc (#FFFFFF), Rouge (#EF4135) - Drapeau français
- **CLI** : Orange (#FF7000) - Couleur Mistral

## Développement

```bash
# Cloner le repo
git clone https://github.com/synoptia/therese-cli
cd therese-cli

# Installer les dépendances dev
uv sync --dev

# Lancer les tests
uv run pytest

# Lancer l'app en dev
uv run therese
```

## Licence

Apache 2.0 - Voir [LICENSE](LICENSE)

## Auteur

**Synoptia** - [synoptia.fr](https://synoptia.fr)

---

*Fait avec ❤️ en France*
