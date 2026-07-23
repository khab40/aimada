from pathlib import Path
from typing import Protocol

from app.data_ingestion.lobster import convert_pair, discover_candidates
from app.data_ingestion.models import DatasetManifest, LobsterCandidate


class IngestionSourceAdapter(Protocol):
    """Administrative source boundary; later adapters may discover other batch or live inputs."""

    source_type: str
    ingestion_mode: str

    def candidates(self) -> list[LobsterCandidate]:
        ...

    def import_candidate(
        self,
        candidate: LobsterCandidate,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> DatasetManifest:
        ...


class LobsterBatchSourceAdapter:
    source_type = "lobster"
    ingestion_mode = "batch"

    def __init__(self, raw_dir: Path, processed_dir: Path) -> None:
        self.raw_dir = raw_dir.resolve()
        self.processed_dir = processed_dir.resolve()

    def candidates(self) -> list[LobsterCandidate]:
        return discover_candidates(self.raw_dir, self.processed_dir)

    def import_candidate(
        self,
        candidate: LobsterCandidate,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> DatasetManifest:
        return convert_pair(
            candidate,
            self.raw_dir,
            self.processed_dir,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
        )
