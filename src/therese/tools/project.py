"""Outils de détection et gestion de projet."""

import json
from pathlib import Path
from typing import Any

from .base import Tool, ToolResult


class ProjectInfo:
    """Informations sur un projet."""

    def __init__(self, path: Path):
        self.path = path
        self.type: str = "unknown"
        self.name: str = path.name
        self.language: str = "unknown"
        self.package_manager: str | None = None
        self.frameworks: list[str] = []
        self.scripts: dict[str, str] = {}
        self.dependencies: list[str] = []

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "type": self.type,
            "name": self.name,
            "language": self.language,
            "package_manager": self.package_manager,
            "frameworks": self.frameworks,
            "scripts": self.scripts,
            "dependencies": self.dependencies[:20],  # Top 20
        }


def detect_project(path: Path) -> ProjectInfo:
    """Détecte le type de projet dans un répertoire."""
    info = ProjectInfo(path)

    # Python (pyproject.toml, setup.py, requirements.txt)
    if (path / "pyproject.toml").exists():
        info.type = "python"
        info.language = "Python"
        info.package_manager = "uv" if (path / "uv.lock").exists() else "pip"
        try:
            import tomllib
            with open(path / "pyproject.toml", "rb") as f:
                data = tomllib.load(f)
            info.name = data.get("project", {}).get("name", info.name)
            deps = data.get("project", {}).get("dependencies", [])
            info.dependencies = [d.split("[")[0].split(">=")[0].split("==")[0] for d in deps]

            # Détecter les frameworks
            dep_str = " ".join(info.dependencies).lower()
            if "fastapi" in dep_str:
                info.frameworks.append("FastAPI")
            if "django" in dep_str:
                info.frameworks.append("Django")
            if "flask" in dep_str:
                info.frameworks.append("Flask")
            if "textual" in dep_str:
                info.frameworks.append("Textual")
            if "pytest" in dep_str:
                info.frameworks.append("pytest")
        except Exception:
            pass

    elif (path / "setup.py").exists():
        info.type = "python"
        info.language = "Python"
        info.package_manager = "pip"

    elif (path / "requirements.txt").exists():
        info.type = "python"
        info.language = "Python"
        info.package_manager = "pip"

    # Node.js (package.json)
    elif (path / "package.json").exists():
        info.type = "node"
        info.language = "JavaScript/TypeScript"

        # Détecter le package manager
        if (path / "bun.lockb").exists():
            info.package_manager = "bun"
        elif (path / "pnpm-lock.yaml").exists():
            info.package_manager = "pnpm"
        elif (path / "yarn.lock").exists():
            info.package_manager = "yarn"
        else:
            info.package_manager = "npm"

        try:
            with open(path / "package.json") as f:
                data = json.load(f)
            info.name = data.get("name", info.name)
            info.scripts = data.get("scripts", {})

            deps = list(data.get("dependencies", {}).keys())
            deps.extend(data.get("devDependencies", {}).keys())
            info.dependencies = deps

            # Détecter les frameworks
            if "next" in deps:
                info.frameworks.append("Next.js")
            if "react" in deps:
                info.frameworks.append("React")
            if "vue" in deps:
                info.frameworks.append("Vue")
            if "svelte" in deps:
                info.frameworks.append("Svelte")
            if "express" in deps:
                info.frameworks.append("Express")
            if "typescript" in deps:
                info.language = "TypeScript"
            if "vite" in deps:
                info.frameworks.append("Vite")
            if "tailwindcss" in deps:
                info.frameworks.append("Tailwind")
        except Exception:
            pass

    # Rust (Cargo.toml)
    elif (path / "Cargo.toml").exists():
        info.type = "rust"
        info.language = "Rust"
        info.package_manager = "cargo"
        try:
            content = (path / "Cargo.toml").read_text()
            # Parser basique
            for line in content.split("\n"):
                if line.startswith("name ="):
                    info.name = line.split("=")[1].strip().strip('"')
                    break
        except Exception:
            pass

    # Go (go.mod)
    elif (path / "go.mod").exists():
        info.type = "go"
        info.language = "Go"
        info.package_manager = "go"

    # Ruby (Gemfile)
    elif (path / "Gemfile").exists():
        info.type = "ruby"
        info.language = "Ruby"
        info.package_manager = "bundler"

    # PHP (composer.json)
    elif (path / "composer.json").exists():
        info.type = "php"
        info.language = "PHP"
        info.package_manager = "composer"

    # Git repo
    if (path / ".git").exists():
        info.frameworks.append("Git")

    # Docker
    if (path / "Dockerfile").exists() or (path / "docker-compose.yml").exists():
        info.frameworks.append("Docker")

    return info


class ProjectDetectTool(Tool):
    """Détecte le type de projet."""

    name = "project_detect"
    description = (
        "Détecte le type de projet, le langage, le package manager et les frameworks utilisés. "
        "Analyse pyproject.toml, package.json, Cargo.toml, etc."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Chemin du projet. Par défaut: répertoire courant",
            },
        },
        "required": [],
    }

    async def execute(
        self,
        path: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Détecte le projet."""
        project_path = Path(path or ".").expanduser().resolve()

        if not project_path.exists():
            return ToolResult(
                success=False,
                output="",
                error=f"Chemin non trouvé: {project_path}",
            )

        info = detect_project(project_path)

        output = [
            f"# 📁 Projet: {info.name}",
            "",
            f"**Type:** {info.type}",
            f"**Langage:** {info.language}",
            f"**Package Manager:** {info.package_manager or 'N/A'}",
        ]

        if info.frameworks:
            output.append(f"**Frameworks:** {', '.join(info.frameworks)}")

        if info.scripts:
            output.append("")
            output.append("## 📜 Scripts disponibles")
            for name, cmd in list(info.scripts.items())[:10]:
                output.append(f"- `{name}`: {cmd[:50]}...")

        if info.dependencies:
            output.append("")
            output.append(f"## 📦 Dépendances ({len(info.dependencies)} total)")
            output.append(", ".join(info.dependencies[:15]))
            if len(info.dependencies) > 15:
                output.append(f"... et {len(info.dependencies) - 15} autres")

        return ToolResult(success=True, output="\n".join(output))


class ProjectRunTool(Tool):
    """Exécute un script du projet."""

    name = "project_run"
    description = (
        "Exécute un script défini dans le projet (npm run, bun run, cargo run, etc.). "
        "Détecte automatiquement le package manager."
    )
    parameters = {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "Nom du script à exécuter (ex: 'dev', 'build', 'test')",
            },
            "args": {
                "type": "string",
                "description": "Arguments supplémentaires",
            },
        },
        "required": ["script"],
    }

    async def execute(
        self,
        script: str,
        args: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        """Exécute un script."""
        import asyncio
        import os

        path = Path.cwd()
        info = detect_project(path)

        # Construire la commande selon le package manager
        if info.package_manager == "bun":
            cmd = f"bun run {script}"
        elif info.package_manager == "pnpm":
            cmd = f"pnpm run {script}"
        elif info.package_manager == "yarn":
            cmd = f"yarn {script}"
        elif info.package_manager == "npm":
            cmd = f"npm run {script}"
        elif info.package_manager == "uv":
            cmd = f"uv run {script}"
        elif info.package_manager == "cargo":
            if script == "run":
                cmd = "cargo run"
            elif script == "build":
                cmd = "cargo build"
            elif script == "test":
                cmd = "cargo test"
            else:
                cmd = f"cargo {script}"
        elif info.package_manager == "go":
            cmd = f"go {script}"
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Package manager non supporté: {info.package_manager}",
            )

        if args:
            cmd += f" {args}"

        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(path),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300,  # 5 minutes
            )

            output = stdout.decode()
            if stderr:
                output += f"\n[stderr]\n{stderr.decode()}"

            return ToolResult(
                success=process.returncode == 0,
                output=output or "(aucune sortie)",
                error=None if process.returncode == 0 else f"Code: {process.returncode}",
            )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Timeout après 5 minutes: {cmd}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Erreur: {e}",
            )
