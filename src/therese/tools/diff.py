"""Outil Diff : affiche les différences entre fichiers ou versions."""

import difflib
from pathlib import Path
from typing import Any

from .base import Tool, ToolResult


class DiffTool(Tool):
    """Affiche les différences entre deux fichiers ou textes."""

    name = "diff"
    description = (
        "Compare deux fichiers ou textes et affiche les différences. "
        "Utile pour voir les changements avant de les appliquer."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file1": {
                "type": "string",
                "description": "Premier fichier ou texte (avec préfixe 'text:' pour du texte brut)",
            },
            "file2": {
                "type": "string",
                "description": "Deuxième fichier ou texte (avec préfixe 'text:' pour du texte brut)",
            },
            "context_lines": {
                "type": "integer",
                "description": "Nombre de lignes de contexte. Par défaut: 3",
            },
            "unified": {
                "type": "boolean",
                "description": "Format unified diff. Par défaut: true",
            },
        },
        "required": ["file1", "file2"],
    }

    async def execute(
        self,
        file1: str,
        file2: str,
        context_lines: int = 3,
        unified: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        """Compare deux fichiers ou textes."""
        try:
            # Charger le premier contenu
            if file1.startswith("text:"):
                content1 = file1[5:].splitlines(keepends=True)
                name1 = "texte1"
            else:
                path1 = Path(file1).expanduser().resolve()
                if not path1.exists():
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Fichier non trouvé: {path1}",
                    )
                content1 = path1.read_text().splitlines(keepends=True)
                name1 = str(path1)

            # Charger le deuxième contenu
            if file2.startswith("text:"):
                content2 = file2[5:].splitlines(keepends=True)
                name2 = "texte2"
            else:
                path2 = Path(file2).expanduser().resolve()
                if not path2.exists():
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Fichier non trouvé: {path2}",
                    )
                content2 = path2.read_text().splitlines(keepends=True)
                name2 = str(path2)

            # Générer le diff
            if unified:
                diff = difflib.unified_diff(
                    content1,
                    content2,
                    fromfile=name1,
                    tofile=name2,
                    n=context_lines,
                )
            else:
                diff = difflib.ndiff(content1, content2)

            diff_text = "".join(diff)

            if not diff_text:
                return ToolResult(
                    success=True,
                    output="Les fichiers sont identiques.",
                )

            # Colorer le diff (pour terminal)
            colored_lines = []
            for line in diff_text.splitlines():
                if line.startswith("+++") or line.startswith("---"):
                    colored_lines.append(f"**{line}**")
                elif line.startswith("+"):
                    colored_lines.append(f"🟢 {line}")
                elif line.startswith("-"):
                    colored_lines.append(f"🔴 {line}")
                elif line.startswith("@@"):
                    colored_lines.append(f"🔵 {line}")
                else:
                    colored_lines.append(f"   {line}")

            return ToolResult(
                success=True,
                output="\n".join(colored_lines),
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur: {e}",
            )


class DiffPreviewTool(Tool):
    """Preview des modifications avant de les appliquer."""

    name = "diff_preview"
    description = (
        "Affiche un aperçu des modifications qui seraient faites par edit_file. "
        "À utiliser avant d'appliquer des changements importants."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Chemin du fichier à modifier",
            },
            "old_string": {
                "type": "string",
                "description": "Chaîne à remplacer",
            },
            "new_string": {
                "type": "string",
                "description": "Nouvelle chaîne",
            },
        },
        "required": ["file_path", "old_string", "new_string"],
    }

    async def execute(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        **kwargs: Any,
    ) -> ToolResult:
        """Affiche un aperçu du changement."""
        try:
            path = Path(file_path).expanduser().resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Fichier non trouvé: {path}",
                )

            content = path.read_text()

            # Vérifier que old_string existe
            count = content.count(old_string)
            if count == 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Chaîne non trouvée dans {path}",
                )

            # Créer le contenu modifié
            new_content = content.replace(old_string, new_string, 1)

            # Générer le diff
            diff = difflib.unified_diff(
                content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{path.name}",
                tofile=f"b/{path.name}",
                n=3,
            )

            diff_text = "".join(diff)

            # Colorer
            colored_lines = [f"# Preview des modifications pour {path}", ""]
            if count > 1:
                colored_lines.append(f"⚠️  {count} occurrences trouvées, seule la première sera modifiée\n")

            for line in diff_text.splitlines():
                if line.startswith("+++") or line.startswith("---"):
                    colored_lines.append(f"**{line}**")
                elif line.startswith("+"):
                    colored_lines.append(f"🟢 {line}")
                elif line.startswith("-"):
                    colored_lines.append(f"🔴 {line}")
                elif line.startswith("@@"):
                    colored_lines.append(f"🔵 {line}")
                else:
                    colored_lines.append(f"   {line}")

            return ToolResult(
                success=True,
                output="\n".join(colored_lines),
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur: {e}",
            )
