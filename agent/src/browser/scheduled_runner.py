from __future__ import annotations

import fcntl
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.browser.queue_runner import preview_browser_queue, run_browser_queue
from src.database.repository import JobRepository
from src.profile.applicant_profile import ApplicantProfile


SCHEDULER_VERSION = 1
SCHEDULED_MAX_LIMIT = 3

MODE_PREVIEW = "PREVIEW"
MODE_BROWSER_DRY_RUN = "BROWSER_DRY_RUN"
MODE_BROWSER_PERSISTED = "BROWSER_PERSISTED"

ALLOWED_MODES = {
    MODE_PREVIEW,
    MODE_BROWSER_DRY_RUN,
    MODE_BROWSER_PERSISTED,
}

ALLOWED_ORDERS = {
    "oldest",
    "newest",
    "fit",
}


class SchedulerConfigError(RuntimeError):
    pass


class SchedulerLockHeld(RuntimeError):
    pass


@dataclass(frozen=True)
class SchedulerConfig:
    mode: str = MODE_PREVIEW
    limit: int = 1
    board_token: str | None = None
    order: str = "oldest"
    profile_path: str = "config/applicant_profile.json"
    resume_dir: str = "resumes"
    queue_artifacts_dir: str = "browser_runs/queue"
    scheduler_artifacts_dir: str = "browser_runs/scheduler"
    delay_seconds: float = 2.0

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SchedulerConfig":
        if not isinstance(raw, dict):
            raise SchedulerConfigError(
                "Scheduler config must be a JSON object."
            )

        mode = str(
            raw.get("mode", MODE_PREVIEW)
        ).strip().upper()

        if mode not in ALLOWED_MODES:
            raise SchedulerConfigError(
                "Invalid scheduler mode."
            )

        try:
            limit = int(raw.get("limit", 1))
        except (TypeError, ValueError):
            raise SchedulerConfigError(
                "Scheduler limit must be an integer."
            )

        if not (1 <= limit <= SCHEDULED_MAX_LIMIT):
            raise SchedulerConfigError(
                "Scheduled Browser Queue limit must be "
                f"between 1 and {SCHEDULED_MAX_LIMIT}."
            )

        order = str(
            raw.get("order", "oldest")
        ).strip().lower()

        if order not in ALLOWED_ORDERS:
            raise SchedulerConfigError(
                "Scheduler order must be one of: "
                "oldest, newest, fit."
            )

        try:
            delay_seconds = float(
                raw.get("delay_seconds", 2.0)
            )
        except (TypeError, ValueError):
            raise SchedulerConfigError(
                "delay_seconds must be numeric."
            )

        if not (0 <= delay_seconds <= 60):
            raise SchedulerConfigError(
                "delay_seconds must be between 0 and 60."
            )

        board_token = raw.get("board_token")
        if board_token is not None:
            board_token = str(board_token).strip()
            if not board_token:
                board_token = None

        return cls(
            mode=mode,
            limit=limit,
            board_token=board_token,
            order=order,
            profile_path=str(
                raw.get(
                    "profile_path",
                    "config/applicant_profile.json",
                )
            ),
            resume_dir=str(
                raw.get("resume_dir", "resumes")
            ),
            queue_artifacts_dir=str(
                raw.get(
                    "queue_artifacts_dir",
                    "browser_runs/queue",
                )
            ),
            scheduler_artifacts_dir=str(
                raw.get(
                    "scheduler_artifacts_dir",
                    "browser_runs/scheduler",
                )
            ),
            delay_seconds=delay_seconds,
        )

    @classmethod
    def load(cls, path: str | Path) -> "SchedulerConfig":
        config_path = Path(path)

        if not config_path.exists():
            raise SchedulerConfigError(
                f"Scheduler config not found: {config_path}"
            )

        try:
            raw = json.loads(
                config_path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise SchedulerConfigError(
                "Scheduler config is not valid JSON."
            ) from exc

        return cls.from_dict(raw)


class SingleRunLock:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._handle = None

    def __enter__(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._handle = self.path.open(
            "a+",
            encoding="utf-8",
        )

        try:
            fcntl.flock(
                self._handle.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError as exc:
            self._handle.close()
            self._handle = None
            raise SchedulerLockHeld(
                "Another scheduled Browser Queue run "
                "is already active."
            ) from exc

        self._handle.seek(0)
        self._handle.truncate(0)
        self._handle.write(str(os.getpid()))
        self._handle.flush()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._handle is None:
            return

        try:
            fcntl.flock(
                self._handle.fileno(),
                fcntl.LOCK_UN,
            )
        finally:
            self._handle.close()
            self._handle = None


def _utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def _safe_candidate(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "board_token": row.get("board_token"),
        "greenhouse_job_id": str(
            row.get("greenhouse_job_id") or ""
        ),
        "company": row.get("company"),
        "title": row.get("title"),
        "application_status": row.get(
            "application_status"
        ),
        "route": row.get("route"),
        "score": row.get("score"),
        "confidence": row.get("confidence"),
    }


def _safe_queue_result(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "board_token": row.get("board_token"),
        "greenhouse_job_id": str(
            row.get("greenhouse_job_id") or ""
        ),
        "company": row.get("company"),
        "title": row.get("title"),
        "queue_status": row.get("queue_status"),
        "outcome": row.get("outcome"),
        "challenge_detected": bool(
            row.get("challenge_detected")
        ),
        "ready_count": int(
            row.get("ready_count") or 0
        ),
        "required_human_count": int(
            row.get("required_human_count") or 0
        ),
        "browser_modified": bool(
            row.get("browser_modified")
        ),
        "submit_clicked_by_agent": False,
        "application_submitted": False,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def run_scheduled_browser_queue(
    *,
    config: SchedulerConfig,
    allow_persisted_mode: bool = False,
    repository: JobRepository | None = None,
    profile_loader=ApplicantProfile.load,
    preview_fn=preview_browser_queue,
    queue_fn=run_browser_queue,
) -> dict[str, Any]:
    """
    Execute one bounded scheduled queue iteration.

    Scheduled V1 is intentionally stricter than manual queue execution:
      - limit 1..3 only
      - PENDING only
      - no IN_PROGRESS opt-in
      - headless only
      - persisted mode requires a second explicit allow flag
    """

    if (
        config.mode == MODE_BROWSER_PERSISTED
        and not allow_persisted_mode
    ):
        raise SchedulerConfigError(
            "Persisted scheduled execution is disabled. "
            "Pass --allow-persisted-mode explicitly."
        )

    repository = repository or JobRepository()

    scheduler_root = Path(
        config.scheduler_artifacts_dir
    )
    lock_path = (
        scheduler_root
        / "browser_queue_scheduler.lock"
    )

    run_key = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    report_path = (
        scheduler_root
        / run_key
        / "scheduled_run.json"
    )

    started_at = _utc_now_iso()

    with SingleRunLock(lock_path):
        if config.mode == MODE_PREVIEW:
            candidates = preview_fn(
                repository=repository,
                limit=config.limit,
                include_in_progress=False,
                board_token=config.board_token,
                order=config.order,
            )

            report = {
                "scheduler_version": SCHEDULER_VERSION,
                "run_key": run_key,
                "mode": config.mode,
                "started_at": started_at,
                "completed_at": _utc_now_iso(),
                "queue_limit": config.limit,
                "board_token_filter": (
                    config.board_token
                ),
                "order": config.order,
                "browser_opened": False,
                "supabase_queue_history_persisted": False,
                "selected_count": len(candidates),
                "candidates": [
                    _safe_candidate(row)
                    for row in candidates
                ],
                "results": [],
                "submit_clicked_by_agent": False,
                "application_submitted": False,
            }

            _write_json(
                report_path,
                report,
            )
            report["report_path"] = str(
                report_path
            )
            return report

        profile = profile_loader(
            config.profile_path
        )

        persist = (
            config.mode
            == MODE_BROWSER_PERSISTED
        )

        queue_report = queue_fn(
            profile=profile,
            repository=repository,
            limit=config.limit,
            include_in_progress=False,
            board_token=config.board_token,
            order=config.order,
            resume_dir=config.resume_dir,
            artifacts_dir=(
                config.queue_artifacts_dir
            ),
            headless=True,
            persist=persist,
            delay_seconds=config.delay_seconds,
        )

        if (
            bool(
                queue_report.get(
                    "submit_clicked_by_agent"
                )
            )
            or bool(
                queue_report.get(
                    "application_submitted"
                )
            )
        ):
            raise RuntimeError(
                "Scheduled Browser Queue blocked: "
                "submission invariant violated."
            )

        if (
            persist
            and not bool(
                queue_report.get(
                    "history_persisted"
                )
            )
        ):
            raise RuntimeError(
                "Scheduled Browser Queue persisted mode "
                "did not persist queue history."
            )

        summary = (
            queue_report.get("summary")
            or {}
        )

        report = {
            "scheduler_version": SCHEDULER_VERSION,
            "run_key": run_key,
            "mode": config.mode,
            "started_at": started_at,
            "completed_at": _utc_now_iso(),
            "queue_limit": config.limit,
            "board_token_filter": (
                config.board_token
            ),
            "order": config.order,
            "browser_opened": True,
            "supabase_queue_history_persisted": bool(
                queue_report.get(
                    "history_persisted"
                )
            ),
            "selected_count": int(
                summary.get("selected") or 0
            ),
            "completed_count": int(
                summary.get("completed") or 0
            ),
            "needs_assistance_count": int(
                summary.get(
                    "needs_assistance"
                )
                or 0
            ),
            "ready_no_submit_count": int(
                summary.get(
                    "ready_no_submit"
                )
                or 0
            ),
            "blocked_count": int(
                summary.get("blocked") or 0
            ),
            "error_count": int(
                summary.get("errors") or 0
            ),
            "challenge_count": int(
                summary.get(
                    "challenge_count"
                )
                or 0
            ),
            "results": [
                _safe_queue_result(row)
                for row in (
                    queue_report.get("results")
                    or []
                )
            ],
            "submit_clicked_by_agent": False,
            "application_submitted": False,
        }

        _write_json(
            report_path,
            report,
        )
        report["report_path"] = str(
            report_path
        )
        return report
