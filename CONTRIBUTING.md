# Contribuer à THÉRÈSE CLI

Merci de votre intérêt pour contribuer à THÉRÈSE ! 🇫🇷

## Comment contribuer

### Signaler un bug

1. Vérifiez que le bug n'a pas déjà été signalé dans les [Issues](https://github.com/ludovicsanchez38-creator/Synoptia-THERESE-CLI/issues)
2. Créez une nouvelle issue avec :
   - Une description claire du problème
   - Les étapes pour reproduire
   - Le comportement attendu vs observé
   - Votre environnement (OS, Python, version THÉRÈSE)

### Proposer une fonctionnalité

1. Ouvrez une issue pour en discuter avant de coder
2. Décrivez le cas d'usage et les bénéfices
3. Attendez le feu vert avant de commencer

### Soumettre du code

1. **Fork** le repo
2. **Clone** votre fork
   ```bash
   git clone https://github.com/votre-username/therese-cli.git
   cd therese-cli
   ```
3. **Créez une branche**
   ```bash
   git checkout -b feature/ma-feature
   # ou
   git checkout -b fix/mon-fix
   ```
4. **Installez les dépendances dev**
   ```bash
   uv sync
   ```
5. **Faites vos modifications**
6. **Testez**
   ```bash
   uv run therese
   ```
7. **Commit** avec un message clair
   ```bash
   git commit -m "feat: ajoute la fonctionnalité X"
   # ou
   git commit -m "fix: corrige le bug Y"
   ```
8. **Push**
   ```bash
   git push origin feature/ma-feature
   ```
9. **Ouvrez une Pull Request**

## Conventions

### Commits

Nous suivons [Conventional Commits](https://www.conventionalcommits.org/) :

- `feat:` nouvelle fonctionnalité
- `fix:` correction de bug
- `docs:` documentation
- `style:` formatage (pas de changement de code)
- `refactor:` refactoring
- `test:` ajout/modification de tests
- `chore:` maintenance

### Code Python

- Python 3.11+
- Formatage avec `ruff format`
- Linting avec `ruff check`
- Type hints recommandés
- Docstrings en français ou anglais

### Structure du code

```
src/therese/
├── agent.py      # Logique de l'agent Mistral
├── commands.py   # Commandes slash
├── config.py     # Configuration
├── memory.py     # Système de mémoire
├── tools/        # Outils (un fichier par catégorie)
└── ui/           # Interface Textual
```

### Ajouter un nouvel outil

1. Créer la classe dans `src/therese/tools/`
2. Hériter de `Tool`
3. Implémenter `name`, `description`, `parameters`, `execute()`
4. Enregistrer dans `src/therese/tools/__init__.py`

Exemple :
```python
from .base import Tool, ToolResult

class MonOutilTool(Tool):
    name = "mon_outil"
    description = "Description de l'outil"
    parameters = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."}
        },
        "required": ["param1"]
    }

    async def execute(self, param1: str, **kwargs) -> ToolResult:
        # Logique ici
        return ToolResult(success=True, output="Résultat")
```

### Ajouter une commande slash

1. Ajouter dans `COMMANDS` dans `src/therese/commands.py`
2. Implémenter la fonction handler

## Questions ?

- Ouvrez une issue
- Contactez [Synoptia](https://synoptia.fr)

Merci ! 🙏
