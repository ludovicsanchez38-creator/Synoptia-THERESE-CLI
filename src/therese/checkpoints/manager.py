"""
Checkpoint Manager pour THERESE CLI.

Gère la création, restauration et listing des checkpoints.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .storage import StorageBase, GitStashStorage, FileStorage, CheckpointData


@dataclass
class Checkpoint:
    """Un checkpoint."""
    id: str
    name: str
    timestamp: datetime
    files: list[str]
    is_auto: bool = False
    description: str = ""

    @classmethod
    def from_data(cls, data: CheckpointData) -> "Checkpoint":
        """Crée un Checkpoint depuis CheckpointData."""
        return cls(
            id=data.id,
            name=data.name,
            timestamp=data.timestamp,
            files=data.files,
            is_auto=data.is_auto,
            description=data.description,
        )


class CheckpointManager:
    """
    Gestionnaire de checkpoints.

    Fonctionnalités :
    - Auto-checkpoint avant modifications
    - Checkpoints nommés
    - Rewind au dernier checkpoint
    - Nettoyage des anciens checkpoints
    """

    MAX_AUTO_CHECKPOINTS = 20  # Garder les N derniers auto-checkpoints
    MAX_NAMED_CHECKPOINTS = 50  # Garder les N derniers checkpoints nommés

    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self._storage = self._detect_storage()
        self._modified_files: set[Path] = set()  # Fichiers modifiés depuis dernier checkpoint
        self._last_auto_cp_id: str | None = None

    def _detect_storage(self) -> StorageBase:
        """Détecte le storage approprié (git ou fichiers)."""
        git_storage = GitStashStorage(self.working_dir)
        if git_storage.is_available():
            return git_storage
        return FileStorage(self.working_dir)

    @property
    def storage_type(self) -> str:
        """Retourne le type de storage utilisé."""
        if isinstance(self._storage, GitStashStorage):
            return "git"
        return "file"

    def _generate_id(self) -> str:
        """Génère un ID unique pour un checkpoint."""
        return f"cp_{uuid.uuid4().hex[:8]}"

    def track_file(self, file_path: Path | str) -> None:
        """Marque un fichier comme modifié (pour auto-checkpoint)."""
        path = Path(file_path) if isinstance(file_path, str) else file_path
        if path.is_relative_to(self.working_dir):
            self._modified_files.add(path)
        else:
            # Chemin absolu - essayer de le rendre relatif
            try:
                self._modified_files.add(path)
            except ValueError:
                pass

    def create(
        self,
        name: str | None = None,
        description: str = "",
        files: list[Path] | None = None,
        is_auto: bool = False,
    ) -> Checkpoint | None:
        """
        Crée un nouveau checkpoint.

        Args:
            name: Nom du checkpoint (auto-généré si None)
            description: Description optionnelle
            files: Fichiers à inclure (tous les modifiés si None)
            is_auto: True si c'est un auto-checkpoint

        Returns:
            Le checkpoint créé ou None si échec
        """
        cp_id = self._generate_id()

        if name is None:
            if is_auto:
                name = f"auto_{datetime.now().strftime('%H%M%S')}"
            else:
                name = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Fichiers à inclure
        if files is None:
            files = list(self._modified_files) if self._modified_files else self._get_modified_files()

        if not files:
            return None  # Rien à sauvegarder

        checkpoint_data = CheckpointData(
            id=cp_id,
            name=name,
            timestamp=datetime.now(),
            files=[str(f) for f in files],
            is_auto=is_auto,
            description=description,
        )

        success = self._storage.save(checkpoint_data, files)
        if not success:
            return None

        # Reset les fichiers trackés
        self._modified_files.clear()

        if is_auto:
            self._last_auto_cp_id = cp_id
            self._cleanup_old_checkpoints(auto_only=True)

        return Checkpoint.from_data(checkpoint_data)

    def _get_modified_files(self) -> list[Path]:
        """Récupère les fichiers modifiés dans le working_dir."""
        # Pour git, on peut utiliser git status
        if isinstance(self._storage, GitStashStorage):
            import subprocess
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=self.working_dir,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    files = []
                    for line in result.stdout.strip().split("\n"):
                        if line.strip():
                            # Format: XY filename
                            filename = line[3:].strip()
                            files.append(self.working_dir / filename)
                    return files
            except Exception:
                pass

        # Fallback : retourner tous les fichiers Python/JS/etc modifiés récemment
        # (dans les 10 dernières minutes)
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(minutes=10)
        files = []

        extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml", ".md"}
        for ext in extensions:
            for f in self.working_dir.rglob(f"*{ext}"):
                if f.is_file():
                    try:
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if mtime > cutoff:
                            files.append(f)
                    except Exception:
                        pass

        return files[:100]  # Limiter à 100 fichiers

    def auto_checkpoint(self, before_action: str = "") -> Checkpoint | None:
        """
        Crée un auto-checkpoint avant une action.

        Args:
            before_action: Description de l'action (ex: "write_file /path/to/file")

        Returns:
            Le checkpoint créé ou None
        """
        return self.create(
            name=None,
            description=f"Avant: {before_action}" if before_action else "",
            is_auto=True,
        )

    def restore(self, checkpoint_id: str | None = None) -> bool:
        """
        Restaure un checkpoint.

        Args:
            checkpoint_id: ID du checkpoint (dernier auto si None)

        Returns:
            True si restauré avec succès
        """
        if checkpoint_id is None:
            # Restaurer le dernier auto-checkpoint
            checkpoint_id = self._last_auto_cp_id
            if not checkpoint_id:
                checkpoints = self.list_checkpoints(auto_only=True)
                if checkpoints:
                    checkpoint_id = checkpoints[0].id
                else:
                    return False

        return self._storage.restore(checkpoint_id)

    def rewind(self) -> tuple[bool, str]:
        """
        Quick rewind au dernier checkpoint.

        Returns:
            (success, message)
        """
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return False, "Aucun checkpoint disponible"

        latest = checkpoints[0]
        success = self.restore(latest.id)

        if success:
            return True, f"Rewind vers '{latest.name}' ({latest.timestamp.strftime('%H:%M:%S')})"
        return False, "Échec du rewind"

    def list_checkpoints(
        self,
        auto_only: bool = False,
        named_only: bool = False,
        limit: int = 20,
    ) -> list[Checkpoint]:
        """
        Liste les checkpoints disponibles.

        Args:
            auto_only: Seulement les auto-checkpoints
            named_only: Seulement les checkpoints nommés
            limit: Nombre max de résultats

        Returns:
            Liste de checkpoints triés par date décroissante
        """
        all_checkpoints = self._storage.list_checkpoints()

        if auto_only:
            all_checkpoints = [cp for cp in all_checkpoints if cp.is_auto]
        elif named_only:
            all_checkpoints = [cp for cp in all_checkpoints if not cp.is_auto]

        return [Checkpoint.from_data(cp) for cp in all_checkpoints[:limit]]

    def get_latest(self) -> Checkpoint | None:
        """Retourne le dernier checkpoint."""
        checkpoints = self.list_checkpoints(limit=1)
        return checkpoints[0] if checkpoints else None

    def get_latest_auto(self) -> Checkpoint | None:
        """Retourne le dernier auto-checkpoint."""
        checkpoints = self.list_checkpoints(auto_only=True, limit=1)
        return checkpoints[0] if checkpoints else None

    def delete(self, checkpoint_id: str) -> bool:
        """Supprime un checkpoint."""
        return self._storage.delete(checkpoint_id)

    def _cleanup_old_checkpoints(self, auto_only: bool = False) -> int:
        """
        Nettoie les anciens checkpoints.

        Returns:
            Nombre de checkpoints supprimés
        """
        if auto_only:
            checkpoints = self.list_checkpoints(auto_only=True, limit=1000)
            max_keep = self.MAX_AUTO_CHECKPOINTS
        else:
            checkpoints = self.list_checkpoints(limit=1000)
            max_keep = self.MAX_AUTO_CHECKPOINTS + self.MAX_NAMED_CHECKPOINTS

        deleted = 0
        if len(checkpoints) > max_keep:
            # Supprimer les plus anciens
            to_delete = checkpoints[max_keep:]
            for cp in to_delete:
                if self.delete(cp.id):
                    deleted += 1

        return deleted

    def to_markdown(self) -> str:
        """Formate les checkpoints en Markdown."""
        checkpoints = self.list_checkpoints(limit=10)

        if not checkpoints:
            return """# 📸 Checkpoints

Aucun checkpoint disponible.

**Usage:**
- `/checkpoint [name]` - Créer un checkpoint
- `/rewind [id]` - Restaurer un checkpoint
- `Esc Esc` - Quick rewind (dernier auto)
"""

        lines = [
            "# 📸 Checkpoints",
            "",
            f"**Storage:** `{self.storage_type}`",
            "",
            "| ID | Nom | Date | Type |",
            "|---|---|---|---|",
        ]

        for cp in checkpoints:
            cp_type = "🔄 auto" if cp.is_auto else "📌 named"
            time_str = cp.timestamp.strftime("%d/%m %H:%M")
            lines.append(f"| `{cp.id}` | {cp.name} | {time_str} | {cp_type} |")

        lines.extend([
            "",
            "**Usage:** `/rewind <id>` ou `Esc Esc` pour quick rewind",
        ])

        return "\n".join(lines)


# Instance globale (lazy)
_manager: CheckpointManager | None = None


def get_checkpoint_manager(working_dir: Path | None = None) -> CheckpointManager:
    """Récupère le gestionnaire de checkpoints (singleton par working_dir)."""
    global _manager

    if working_dir is None:
        from ..config import config
        working_dir = config.working_dir

    if _manager is None or _manager.working_dir != working_dir:
        _manager = CheckpointManager(working_dir)

    return _manager
