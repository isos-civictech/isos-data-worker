"""
Execution results — the common vocabulary for use cases.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

FAILURE_RATE_THRESHOLD = 0.2


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class SaveOutcome:
    """
    Outcome of saving an entity.
    """

    entity_id: int | str
    created: bool


@dataclass(frozen=True)
class BatchOutcome:
    created: int
    updated: int


@dataclass
class SyncReport:
    """
    Execution report for a run, returned as-is by the CLI and the API.

    The counters are deliberately separated:
        processed  seen in the source
        created    inserted
        updated    already present, updated
        skipped    intentionally ignored (dry-run, type without destination)
        failed     unexpected error, logged, run continued
    """

    entity: str
    started_at: datetime = field(default_factory=_now)
    finished_at: datetime | None = None

    processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0

    errors: list[str] = field(default_factory=list)

    ERROR_SAMPLE_SIZE = 20

    def record_failure(self, uid: str) -> None:
        self.failed += 1
        if len(self.errors) < self.ERROR_SAMPLE_SIZE:
            self.errors.append(uid)

    def finish(self) -> "SyncReport":
        self.finished_at = _now()
        return self

    @property
    def duration_s(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def ok(self) -> bool:
        """False on an empty run or above the failure threshold."""
        if self.processed == 0:
            return False
        return self.failed / self.processed <= FAILURE_RATE_THRESHOLD

    def as_dict(self) -> dict:
        """Return a dictionary representation of the sync report."""
        return {
            "entity": self.entity,
            "ok": self.ok,
            "processed": self.processed,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
            "duration_s": self.duration_s,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "errors": self.errors,
        }
