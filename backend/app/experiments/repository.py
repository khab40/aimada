import re
import shutil
from pathlib import Path

from app.experiments.models import Experiment
from app.storage.local_store import LocalStore


EXPERIMENT_ID_PATTERN = re.compile(r"^[A-Z0-9_-]+$")


class ExperimentRepository:
    def __init__(self, store: LocalStore) -> None:
        self.store = store

    def save(self, experiment: Experiment) -> Experiment:
        self.store.write_json(self._relative_manifest_path(experiment.id), experiment.model_dump(mode="json"))
        return experiment

    def list(self) -> list[Experiment]:
        experiments: list[Experiment] = []
        root = self.store.output_dir / "experiments"
        if not root.exists():
            return []
        for manifest in sorted(root.glob("*/experiment.json")):
            loaded = self._load_manifest(manifest)
            if loaded is not None:
                experiments.append(loaded)
        return sorted(experiments, key=lambda experiment: experiment.created_at, reverse=True)

    def get(self, experiment_id: str) -> Experiment | None:
        path = self._manifest_path(experiment_id)
        if not path.exists():
            return None
        return self._load_manifest(path)

    def delete(self, experiment_id: str) -> bool:
        path = self._experiment_dir(experiment_id)
        if not path.exists():
            return False
        if not path.is_dir():
            return False
        shutil.rmtree(path)
        return True

    def experiment_dir(self, experiment_id: str) -> Path:
        return self._experiment_dir(experiment_id)

    def _load_manifest(self, path: Path) -> Experiment | None:
        try:
            return Experiment.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            return None

    def _relative_manifest_path(self, experiment_id: str) -> str:
        return f"experiments/{self._safe_id(experiment_id)}/experiment.json"

    def _manifest_path(self, experiment_id: str) -> Path:
        return self._experiment_dir(experiment_id) / "experiment.json"

    def _experiment_dir(self, experiment_id: str) -> Path:
        return self.store.output_dir / "experiments" / self._safe_id(experiment_id)

    def _safe_id(self, experiment_id: str) -> str:
        normalized = experiment_id.strip().upper()
        if not normalized or not EXPERIMENT_ID_PATTERN.match(normalized):
            raise ValueError(f"invalid experiment id: {experiment_id}")
        return normalized
