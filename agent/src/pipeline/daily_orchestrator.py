from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.browser.scheduled_runner import (
    MODE_BROWSER_DRY_RUN,
    MODE_BROWSER_PERSISTED,
    SchedulerConfig,
    run_scheduled_browser_queue,
)
from src.browser.queue_runner import preview_browser_queue
from src.database.repository import JobRepository


DAILY_PIPELINE_VERSION = 1
DAILY_MAX_BROWSER_LIMIT = 3

MODE_SCAN_ONLY = "SCAN_ONLY"
MODE_SCAN_THEN_BROWSER_DRY_RUN = (
    "SCAN_THEN_BROWSER_DRY_RUN"
)
MODE_SCAN_THEN_BROWSER_PERSISTED = (
    "SCAN_THEN_BROWSER_PERSISTED"
)

ALLOWED_MODES = {
    MODE_SCAN_ONLY,
    MODE_SCAN_THEN_BROWSER_DRY_RUN,
    MODE_SCAN_THEN_BROWSER_PERSISTED,
}

ALLOWED_ORDERS = {
    "oldest",
    "newest",
    "fit",
}


class DailyPipelineConfigError(RuntimeError):
    pass


class DailyPipelineBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class DailyPipelineConfig:
    mode: str = MODE_SCAN_ONLY
    scan_entrypoint: str = "main.py"
    browser_limit: int = 1
    browser_board_token: str | None = None
    browser_order: str = "oldest"
    profile_path: str = "config/applicant_profile.json"
    resume_dir: str = "resumes"
    browser_queue_artifacts_dir: str = "browser_runs/queue"
    browser_scheduler_artifacts_dir: str = "browser_runs/scheduler"
    pipeline_artifacts_dir: str = "browser_runs/pipeline"
    browser_delay_seconds: float = 2.0
    post_scan_delay_seconds: float = 1.0

    @classmethod
    def from_dict(
        cls,
        raw: dict[str, Any],
    ) -> "DailyPipelineConfig":
        if not isinstance(raw, dict):
            raise DailyPipelineConfigError(
                "Daily pipeline config must be a JSON object."
            )

        mode = str(
            raw.get("mode", MODE_SCAN_ONLY)
        ).strip().upper()

        if mode not in ALLOWED_MODES:
            raise DailyPipelineConfigError(
                "Invalid daily pipeline mode."
            )

        try:
            browser_limit = int(
                raw.get("browser_limit", 1)
            )
        except (TypeError, ValueError):
            raise DailyPipelineConfigError(
                "browser_limit must be an integer."
            )

        if not (
            1
            <= browser_limit
            <= DAILY_MAX_BROWSER_LIMIT
        ):
            raise DailyPipelineConfigError(
                "Daily browser limit must be between "
                f"1 and {DAILY_MAX_BROWSER_LIMIT}."
            )

        browser_order = str(
            raw.get(
                "browser_order",
                "oldest",
            )
        ).strip().lower()

        if browser_order not in ALLOWED_ORDERS:
            raise DailyPipelineConfigError(
                "browser_order must be one of: "
                "oldest, newest, fit."
            )

        browser_board_token = raw.get(
            "browser_board_token"
        )

        if browser_board_token is not None:
            browser_board_token = str(
                browser_board_token
            ).strip()

            if not browser_board_token:
                browser_board_token = None

        try:
            browser_delay_seconds = float(
                raw.get(
                    "browser_delay_seconds",
                    2.0,
                )
            )
        except (TypeError, ValueError):
            raise DailyPipelineConfigError(
                "browser_delay_seconds must be numeric."
            )

        if not (
            0
            <= browser_delay_seconds
            <= 60
        ):
            raise DailyPipelineConfigError(
                "browser_delay_seconds must be between 0 and 60."
            )

        try:
            post_scan_delay_seconds = float(
                raw.get(
                    "post_scan_delay_seconds",
                    1.0,
                )
            )
        except (TypeError, ValueError):
            raise DailyPipelineConfigError(
                "post_scan_delay_seconds must be numeric."
            )

        if not (
            0
            <= post_scan_delay_seconds
            <= 30
        ):
            raise DailyPipelineConfigError(
                "post_scan_delay_seconds must be between 0 and 30."
            )

        scan_entrypoint = str(
            raw.get(
                "scan_entrypoint",
                "main.py",
            )
        ).strip()

        if not scan_entrypoint:
            raise DailyPipelineConfigError(
                "scan_entrypoint cannot be empty."
            )

        return cls(
            mode=mode,
            scan_entrypoint=scan_entrypoint,
            browser_limit=browser_limit,
            browser_board_token=browser_board_token,
            browser_order=browser_order,
            profile_path=str(
                raw.get(
                    "profile_path",
                    "config/applicant_profile.json",
                )
            ),
            resume_dir=str(
                raw.get(
                    "resume_dir",
                    "resumes",
                )
            ),
            browser_queue_artifacts_dir=str(
                raw.get(
                    "browser_queue_artifacts_dir",
                    "browser_runs/queue",
                )
            ),
            browser_scheduler_artifacts_dir=str(
                raw.get(
                    "browser_scheduler_artifacts_dir",
                    "browser_runs/scheduler",
                )
            ),
            pipeline_artifacts_dir=str(
                raw.get(
                    "pipeline_artifacts_dir",
                    "browser_runs/pipeline",
                )
            ),
            browser_delay_seconds=browser_delay_seconds,
            post_scan_delay_seconds=post_scan_delay_seconds,
        )

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> "DailyPipelineConfig":
        config_path = Path(path)

        if not config_path.exists():
            raise DailyPipelineConfigError(
                f"Daily pipeline config not found: {config_path}"
            )

        try:
            raw = json.loads(
                config_path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError as exc:
            raise DailyPipelineConfigError(
                "Daily pipeline config is not valid JSON."
            ) from exc

        return cls.from_dict(raw)


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def parse_utc(
    value: str | None,
) -> datetime | None:
    if not value:
        return None

    text = str(value).strip()

    if text.endswith("Z"):
        text = (
            text[:-1]
            + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            text
        )
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return parsed.astimezone(
        timezone.utc
    )


def _write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
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


def _run_scan_subprocess(
    *,
    agent_dir: Path,
    scan_entrypoint: str,
    stdout_path: Path,
    stderr_path: Path,
) -> dict[str, Any]:
    entrypoint = (
        agent_dir
        / scan_entrypoint
    )

    if not entrypoint.exists():
        raise DailyPipelineBlocked(
            f"Scanner entrypoint not found: {entrypoint}"
        )

    stdout_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    started = time.perf_counter()

    with (
        stdout_path.open(
            "w",
            encoding="utf-8",
        ) as stdout_handle,
        stderr_path.open(
            "w",
            encoding="utf-8",
        ) as stderr_handle,
    ):
        completed = subprocess.run(
            [
                sys.executable,
                "-u",
                str(entrypoint),
            ],
            cwd=str(agent_dir),
            stdout=stdout_handle,
            stderr=stderr_handle,
            check=False,
        )

    return {
        "return_code": (
            int(
                completed.returncode
            )
        ),
        "total_seconds": round(
            (
                time.perf_counter()
                - started
            ),
            3,
        ),
    }


def get_fresh_completed_scan(
    *,
    repository: JobRepository,
    scan_started_at: str,
) -> dict[str, Any] | None:
    response = (
        repository.client
        .table(
            "agent_runs"
        )
        .select(
            (
                "board_token,"
                "started_at,"
                "completed_at,"
                "jobs_discovered,"
                "target_role_jobs,"
                "us_compatible_jobs,"
                "jobs_eligible,"
                "manual_priority_count,"
                "agent_apply_count,"
                "experience_rejected_count,"
                "unknown_location_count,"
                "total_seconds"
            )
        )
        .eq(
            "owner_id",
            repository.owner_id,
        )
        .eq(
            "board_token",
            "multi",
        )
        .gte(
            "started_at",
            scan_started_at,
        )
        .order(
            "started_at",
            desc=True,
        )
        .limit(
            5
        )
        .execute()
    )

    rows = (
        response.data
        or []
    )

    for row in rows:
        if row.get(
            "completed_at"
        ):
            return dict(
                row
            )

    return None


def _safe_scan_summary(
    scan: dict[str, Any],
) -> dict[str, Any]:
    return {
        "board_token": (
            scan.get(
                "board_token"
            )
        ),
        "started_at": (
            scan.get(
                "started_at"
            )
        ),
        "completed_at": (
            scan.get(
                "completed_at"
            )
        ),
        "jobs_discovered": int(
            scan.get(
                "jobs_discovered"
            )
            or 0
        ),
        "target_role_jobs": int(
            scan.get(
                "target_role_jobs"
            )
            or 0
        ),
        "us_compatible_jobs": int(
            scan.get(
                "us_compatible_jobs"
            )
            or 0
        ),
        "jobs_eligible": int(
            scan.get(
                "jobs_eligible"
            )
            or 0
        ),
        "manual_priority_count": int(
            scan.get(
                "manual_priority_count"
            )
            or 0
        ),
        "agent_apply_count": int(
            scan.get(
                "agent_apply_count"
            )
            or 0
        ),
        "experience_rejected_count": int(
            scan.get(
                "experience_rejected_count"
            )
            or 0
        ),
        "unknown_location_count": int(
            scan.get(
                "unknown_location_count"
            )
            or 0
        ),
        "total_seconds": float(
            scan.get(
                "total_seconds"
            )
            or 0
        ),
    }


def _safe_candidate(
    row: dict[str, Any],
) -> dict[str, Any]:
    return {
        "board_token": (
            row.get(
                "board_token"
            )
        ),
        "greenhouse_job_id": str(
            row.get(
                "greenhouse_job_id"
            )
            or ""
        ),
        "company": (
            row.get(
                "company"
            )
        ),
        "title": (
            row.get(
                "title"
            )
        ),
        "route": (
            row.get(
                "route"
            )
        ),
        "application_status": (
            row.get(
                "application_status"
            )
        ),
        "score": (
            row.get(
                "score"
            )
        ),
        "confidence": (
            row.get(
                "confidence"
            )
        ),
        "evaluation_completed_at": (
            row.get(
                "evaluation_completed_at"
            )
        ),
    }


def assert_fresh_browser_candidates(
    *,
    candidates: list[dict[str, Any]],
    scan_started_at: str,
) -> None:
    scan_started = parse_utc(
        scan_started_at
    )

    if scan_started is None:
        raise DailyPipelineBlocked(
            "Could not parse scan start timestamp."
        )

    for candidate in candidates:
        evaluation_completed = parse_utc(
            candidate.get(
                "evaluation_completed_at"
            )
        )

        if (
            evaluation_completed is None
            or evaluation_completed
            < scan_started
        ):
            raise DailyPipelineBlocked(
                "Browser queue candidate is stale relative "
                "to the just-completed scan."
            )


def _browser_mode_for_pipeline(
    mode: str,
) -> str:
    if (
        mode
        == MODE_SCAN_THEN_BROWSER_DRY_RUN
    ):
        return (
            MODE_BROWSER_DRY_RUN
        )

    if (
        mode
        == MODE_SCAN_THEN_BROWSER_PERSISTED
    ):
        return (
            MODE_BROWSER_PERSISTED
        )

    raise DailyPipelineConfigError(
        "Pipeline mode does not include a browser stage."
    )


def run_daily_pipeline(
    *,
    config: DailyPipelineConfig,
    allow_browser_persistence: bool = False,
    agent_dir: str | Path = ".",
    repository: JobRepository | None = None,
    scan_runner=_run_scan_subprocess,
    scan_lookup=get_fresh_completed_scan,
    preview_fn=preview_browser_queue,
    scheduled_browser_fn=run_scheduled_browser_queue,
) -> dict[str, Any]:
    if (
        config.mode
        == MODE_SCAN_THEN_BROWSER_PERSISTED
        and not allow_browser_persistence
    ):
        raise DailyPipelineConfigError(
            "Persisted browser stage is disabled. "
            "Pass --allow-browser-persistence explicitly."
        )

    agent_dir = Path(
        agent_dir
    ).resolve()

    repository = (
        repository
        or JobRepository()
    )

    pipeline_root = Path(
        config.pipeline_artifacts_dir
    )

    if not pipeline_root.is_absolute():
        pipeline_root = (
            agent_dir
            / pipeline_root
        )

    run_key = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    run_dir = (
        pipeline_root
        / run_key
    )

    report_path = (
        run_dir
        / "daily_pipeline_report.json"
    )

    scan_stdout_path = (
        run_dir
        / "scan.stdout.log"
    )

    scan_stderr_path = (
        run_dir
        / "scan.stderr.log"
    )

    pipeline_started_at = (
        utc_now_iso()
    )

    scan_started_at = (
        utc_now_iso()
    )

    scan_execution = scan_runner(
        agent_dir=agent_dir,
        scan_entrypoint=(
            config.scan_entrypoint
        ),
        stdout_path=(
            scan_stdout_path
        ),
        stderr_path=(
            scan_stderr_path
        ),
    )

    if int(
        scan_execution.get(
            "return_code",
            1,
        )
    ) != 0:
        raise DailyPipelineBlocked(
            "Greenhouse scan exited non-zero. "
            "Browser stage was not started."
        )

    scan = scan_lookup(
        repository=repository,
        scan_started_at=(
            scan_started_at
        ),
    )

    if not scan:
        raise DailyPipelineBlocked(
            "No fresh completed multi-company agent run "
            "was found after the scan process exited."
        )

    safe_scan = (
        _safe_scan_summary(
            scan
        )
    )

    if (
        safe_scan[
            "jobs_discovered"
        ]
        <= 0
    ):
        raise DailyPipelineBlocked(
            "Fresh scan discovered zero jobs. "
            "Browser stage was blocked."
        )

    if (
        config.post_scan_delay_seconds
        > 0
    ):
        time.sleep(
            config.post_scan_delay_seconds
        )

    base_report = {
        "pipeline_version": (
            DAILY_PIPELINE_VERSION
        ),
        "run_key": (
            run_key
        ),
        "mode": (
            config.mode
        ),
        "started_at": (
            pipeline_started_at
        ),
        "scan": (
            safe_scan
        ),
        "scan_process_seconds": (
            float(
                scan_execution.get(
                    "total_seconds",
                    0,
                )
                or 0
            )
        ),
        "browser_limit": (
            config.browser_limit
        ),
        "browser_board_token_filter": (
            config.browser_board_token
        ),
        "browser_order": (
            config.browser_order
        ),
        "browser_opened": False,
        "browser_history_persisted": False,
        "browser_selected_count": 0,
        "browser_candidates": [],
        "submit_clicked_by_agent": False,
        "application_submitted": False,
    }

    if (
        config.mode
        == MODE_SCAN_ONLY
    ):
        base_report[
            "completed_at"
        ] = utc_now_iso()

        base_report[
            "status"
        ] = "COMPLETED_SCAN_ONLY"

        _write_json(
            report_path,
            base_report,
        )

        base_report[
            "report_path"
        ] = str(
            report_path
        )

        return (
            base_report
        )

    candidates = preview_fn(
        repository=repository,
        limit=config.browser_limit,
        include_in_progress=False,
        board_token=(
            config.browser_board_token
        ),
        order=(
            config.browser_order
        ),
    )

    base_report[
        "browser_candidates"
    ] = [
        _safe_candidate(
            row
        )
        for row in (
            candidates
        )
    ]

    if not candidates:
        base_report[
            "completed_at"
        ] = utc_now_iso()

        base_report[
            "status"
        ] = "COMPLETED_NO_BROWSER_CANDIDATES"

        _write_json(
            report_path,
            base_report,
        )

        base_report[
            "report_path"
        ] = str(
            report_path
        )

        return (
            base_report
        )

    assert_fresh_browser_candidates(
        candidates=candidates,
        scan_started_at=(
            scan_started_at
        ),
    )

    browser_mode = (
        _browser_mode_for_pipeline(
            config.mode
        )
    )

    scheduler_config = (
        SchedulerConfig.from_dict(
            {
                "mode": (
                    browser_mode
                ),
                "limit": (
                    config.browser_limit
                ),
                "board_token": (
                    config.browser_board_token
                ),
                "order": (
                    config.browser_order
                ),
                "profile_path": (
                    config.profile_path
                ),
                "resume_dir": (
                    config.resume_dir
                ),
                "queue_artifacts_dir": (
                    config.browser_queue_artifacts_dir
                ),
                "scheduler_artifacts_dir": (
                    config.browser_scheduler_artifacts_dir
                ),
                "delay_seconds": (
                    config.browser_delay_seconds
                ),
            }
        )
    )

    browser_report = (
        scheduled_browser_fn(
            config=scheduler_config,
            allow_persisted_mode=(
                allow_browser_persistence
            ),
            repository=repository,
        )
    )

    if (
        bool(
            browser_report.get(
                "submit_clicked_by_agent"
            )
        )
        or bool(
            browser_report.get(
                "application_submitted"
            )
        )
    ):
        raise DailyPipelineBlocked(
            "Daily pipeline submission invariant violated."
        )

    browser_history_persisted = (
        bool(
            browser_report.get(
                "supabase_queue_history_persisted"
            )
        )
    )

    if (
        config.mode
        == MODE_SCAN_THEN_BROWSER_PERSISTED
        and not browser_history_persisted
    ):
        raise DailyPipelineBlocked(
            "Persisted daily browser stage did not "
            "persist Browser Queue history."
        )

    base_report.update(
        {
            "completed_at": (
                utc_now_iso()
            ),
            "status": (
                "COMPLETED_BROWSER"
            ),
            "browser_opened": bool(
                browser_report.get(
                    "browser_opened"
                )
            ),
            "browser_history_persisted": (
                browser_history_persisted
            ),
            "browser_selected_count": int(
                browser_report.get(
                    "selected_count"
                )
                or 0
            ),
            "submit_clicked_by_agent": False,
            "application_submitted": False,
        }
    )

    _write_json(
        report_path,
        base_report,
    )

    base_report[
        "report_path"
    ] = str(
        report_path
    )

    return (
        base_report
    )
