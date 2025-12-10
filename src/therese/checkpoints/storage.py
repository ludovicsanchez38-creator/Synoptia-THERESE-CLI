"""
Storage backends pour les checkpoints.

Deux backends :
- GitStashStorage : utilise git stash (si repo git)
- FileStorage : archive tar.gz (fallback)
"""

import hashlib
import json
import shutil
import subprocess
import tarfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator


@dataclass
class CheckpointData:
    """Données d'un checkpoint."""
    id: str
    name: str
    timestamp: datetime
    files: list[str]  # Fichiers inclus
    is_auto: bool = False
    description: str = ""


class StorageBase(ABC):
    """Interface abstraite pour le stockage des checkpoints."""

    @abstractmethod
    def save(self, checkpoint: CheckpointData, files: list[Path]) -> bool:
        """Sauvegarde un checkpoint."""
        ...

    @abstractmethod
    def restore(self, checkpoint_id: str) -> bool:
        """Restaure un checkpoint."""
        ...

    @abstractmethod
    def list_checkpoints(self) -> list[CheckpointData]:
        """Liste les checkpoints disponibles."""
        ...

    @abstractmethod
    def delete(self, checkpoint_id: str) -> bool:
        """Supprime un checkpoint."""
        ...


class GitStashStorage(StorageBase):
    """
    Storage utilisant git stash.

    Avantages :
    - Efficace (diff-based)
    - Intégré avec git
    - Supporte les fichiers non trackés
    """

    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self._index_file = working_dir / ".git" / "therese_checkpoints.json"

    def is_available(self) -> bool:
        """Vérifie si le repo git est disponible."""
        git_dir = self.working_dir / ".git"
        return git_dir.exists() and git_dir.is_dir()

    def _load_index(self) -> dict:
        """Charge l'index des checkpoints."""
        if self._index_file.exists():
            return json.loads(self._index_file.read_text())
        return {"checkpoints": []}

    def _save_index(self, index: dict) -> None:
        """Sauvegarde l'index."""
        self._index_file.write_text(json.dumps(index, indent=2, default=str))

    def _run_git(self, *args) -> tuple[bool, str]:
        """Exécute une commande git."""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.working_dir,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def save(self, checkpoint: CheckpointData, files: list[Path]) -> bool:
        """Sauvegarde via git stash."""
        # Ajouter les fichiers non trackés au stash
        stash_msg = f"THERESE_CP:{checkpoint.id}:{checkpoint.name}"

        # Stash incluant les fichiers non trackés
        success, output = self._run_git("stash", "push", "-u", "-m", stash_msg)
        if not success:
            # Rien à stash (pas de changements)
            return False

        # Enregistrer dans l'index
        index = self._load_index()
        index["checkpoints"].append({
            "id": checkpoint.id,
            "name": checkpoint.name,
            "timestamp": checkpoint.timestamp.isoformat(),
            "files": checkpoint.files,
            "is_auto": checkpoint.is_auto,
            "description": checkpoint.description,
            "stash_ref": f"stash@{{0}}",  # Le dernier stash
        })
        self._save_index(index)

        return True

    def restore(self, checkpoint_id: str) -> bool:
        """Restaure depuis git stash."""
        index = self._load_index()

        # Trouver le checkpoint
        cp_data = None
        for cp in index["checkpoints"]:
            if cp["id"] == checkpoint_id:
                cp_data = cp
                break

        if not cp_data:
            return False

        # Trouver le stash correspondant
        success, stash_list = self._run_git("stash", "list")
        if not success:
            return False

        stash_ref = None
        for line in stash_list.strip().split("\n"):
            if f"THERESE_CP:{checkpoint_id}:" in line:
                # Extraire la ref (ex: stash@{0})
                stash_ref = line.split(":")[0]
                break

        if not stash_ref:
            return False

        # Restaurer le stash
        success, _ = self._run_git("stash", "pop", stash_ref)
        return success

    def list_checkpoints(self) -> list[CheckpointData]:
        """Liste les checkpoints depuis l'index."""
        index = self._load_index()
        checkpoints = []

        for cp in index["checkpoints"]:
            checkpoints.append(CheckpointData(
                id=cp["id"],
                name=cp["name"],
                timestamp=datetime.fromisoformat(cp["timestamp"]),
                files=cp.get("files", []),
                is_auto=cp.get("is_auto", False),
                description=cp.get("description", ""),
            ))

        return sorted(checkpoints, key=lambda x: x.timestamp, reverse=True)

    def delete(self, checkpoint_id: str) -> bool:
        """Supprime un checkpoint."""
        index = self._load_index()
        index["checkpoints"] = [
            cp for cp in index["checkpoints"]
            if cp["id"] != checkpoint_id
        ]
        self._save_index(index)
        return True


class FileStorage(StorageBase):
    """
    Storage utilisant des archives tar.gz.

    Fallback pour les projets sans git.
    """

    def __init__(self, working_dir: Path, storage_dir: Path | None = None):
        self.working_dir = working_dir
        self.storage_dir = storage_dir or (
            Path.home() / ".therese" / "checkpoints" / self._project_hash()
        )
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.storage_dir / "index.json"

    def _project_hash(self) -> str:
        """Hash du chemin du projet pour nommage unique."""
        return hashlib.md5(str(self.working_dir).encode()).hexdigest()[:12]

    def _load_index(self) -> dict:
        """Charge l'index des checkpoints."""
        if self._index_file.exists():
            return json.loads(self._index_file.read_text())
        return {"checkpoints": []}

    def _save_index(self, index: dict) -> None:
        """Sauvegarde l'index."""
        self._index_file.write_text(json.dumps(index, indent=2, default=str))

    def save(self, checkpoint: CheckpointData, files: list[Path]) -> bool:
        """Sauvegarde les fichiers dans une archive tar.gz."""
        archive_path = self.storage_dir / f"{checkpoint.id}.tar.gz"

        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                for file_path in files:
                    if file_path.exists():
                        # Chemin relatif au working_dir
                        arcname = file_path.relative_to(self.working_dir)
                        tar.add(file_path, arcname=str(arcname))

            # Mettre à jour l'index
            index = self._load_index()
            index["checkpoints"].append({
                "id": checkpoint.id,
                "name": checkpoint.name,
                "timestamp": checkpoint.timestamp.isoformat(),
                "files": [str(f.relative_to(self.working_dir)) for f in files if f.exists()],
                "is_auto": checkpoint.is_auto,
                "description": checkpoint.description,
                "archive": str(archive_path),
            })
            self._save_index(index)

            return True
        except Exception:
            return False

    def restore(self, checkpoint_id: str) -> bool:
        """Restaure les fichiers depuis l'archive."""
        index = self._load_index()

        # Trouver le checkpoint
        cp_data = None
        for cp in index["checkpoints"]:
            if cp["id"] == checkpoint_id:
                cp_data = cp
                break

        if not cp_data:
            return False

        archive_path = Path(cp_data.get("archive", ""))
        if not archive_path.exists():
            return False

        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(self.working_dir)
            return True
        except Exception:
            return False

    def list_checkpoints(self) -> list[CheckpointData]:
        """Liste les checkpoints depuis l'index."""
        index = self._load_index()
        checkpoints = []

        for cp in index["checkpoints"]:
            checkpoints.append(CheckpointData(
                id=cp["id"],
                name=cp["name"],
                timestamp=datetime.fromisoformat(cp["timestamp"]),
                files=cp.get("files", []),
                is_auto=cp.get("is_auto", False),
                description=cp.get("description", ""),
            ))

        return sorted(checkpoints, key=lambda x: x.timestamp, reverse=True)

    def delete(self, checkpoint_id: str) -> bool:
        """Supprime un checkpoint et son archive."""
        index = self._load_index()

        # Trouver et supprimer l'archive
        for cp in index["checkpoints"]:
            if cp["id"] == checkpoint_id:
                archive_path = Path(cp.get("archive", ""))
                if archive_path.exists():
                    archive_path.unlink()
                break

        # Mettre à jour l'index
        index["checkpoints"] = [
            cp for cp in index["checkpoints"]
            if cp["id"] != checkpoint_id
        ]
        self._save_index(index)
        return True
