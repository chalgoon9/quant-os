from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

from quant_os.normalization import ValidationIssue, ValidationReport


class IngestionArtifactStore:
    def __init__(self, *, data_root: Path, artifacts_root: Path) -> None:
        self.data_root = Path(data_root)
        self.artifacts_root = Path(artifacts_root)
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.artifacts_root.mkdir(parents=True, exist_ok=True)

    def save_raw_payload(
        self,
        *,
        source: str,
        dataset: str,
        fetched_at: datetime,
        request_params: dict[str, str],
        payload: list[dict[str, object]],
    ) -> Path:
        path = self.data_root / "raw" / source / dataset / f"{_stamp(fetched_at)}.json"
        _write_json(
            path,
            {
                "source": source,
                "dataset": dataset,
                "fetched_at": fetched_at.astimezone(timezone.utc).isoformat(),
                "request_params": request_params,
                "record_count": len(payload),
                "payload": payload,
            },
        )
        return path

    def save_validation_report(
        self,
        *,
        source: str,
        dataset: str,
        fetched_at: datetime,
        raw_archive_path: Path,
        report: ValidationReport,
    ) -> Path:
        path = self.artifacts_root / "validation" / source / dataset / f"{_stamp(fetched_at)}.json"
        _write_json(
            path,
            {
                **report.to_payload(),
                "dataset": dataset,
                "raw_archive_path": str(raw_archive_path),
            },
        )
        return path

    def save_quarantine_records(
        self,
        *,
        source: str,
        dataset: str,
        fetched_at: datetime,
        issues: tuple[ValidationIssue, ...],
    ) -> Path | None:
        if not issues:
            return None
        path = self.artifacts_root / "quarantine" / source / dataset / f"{_stamp(fetched_at)}.json"
        _write_json(
            path,
            {
                "source": source,
                "dataset": dataset,
                "fetched_at": fetched_at.astimezone(timezone.utc).isoformat(),
                "invalid_records": len(issues),
                "issues": [issue.to_payload() for issue in issues],
            },
        )
        return path


def _stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
