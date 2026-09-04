from __future__ import annotations

import json
import time
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from src.browser.orchestrator import (
    orchestrate_browser_application,
)
from src.database.repository import (
    JobRepository,
)
from src.profile.applicant_profile import (
    ApplicantProfile,
)


def _utc_now_iso() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )


def _utc_run_id() -> str:
    return (
        datetime.now(
            timezone.utc
        )
        .strftime(
            "%Y%m%dT%H%M%SZ"
        )
    )


def _write_json(
    path: Path,
    payload: dict,
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


def preview_browser_queue(
    *,
    repository: JobRepository | None = None,
    limit: int = 3,
    include_in_progress: bool = False,
    board_token: str | None = None,
    order: str = "oldest",
) -> list[dict]:
    """
    Return the current queue without opening a browser.
    """

    repository = (
        repository
        or JobRepository()
    )

    return (
        repository
        .list_browser_queue_candidates(
            limit=limit,
            include_in_progress=(
                include_in_progress
            ),
            board_token=(
                board_token
            ),
            order=order,
        )
    )


def run_browser_queue(
    *,
    profile: ApplicantProfile,
    repository: JobRepository | None = None,
    limit: int = 3,
    include_in_progress: bool = False,
    board_token: str | None = None,
    order: str = "oldest",
    resume_dir: str | Path = "resumes",
    artifacts_dir: str | Path = "browser_runs/queue",
    headless: bool = True,
    persist: bool = False,
    delay_seconds: float = 2.0,
    run_id: str | None = None,
    orchestrate_fn=(
        orchestrate_browser_application
    ),
    sleep_fn=time.sleep,
    monotonic_fn=time.monotonic,
) -> dict:
    """
    Browser Queue Runner V1.

    Executes a bounded list of safe AGENT_APPLY jobs one at a time.
    Every job is isolated: a blocked/error job is recorded and the
    queue continues.

    Persistence is opt-in. No code path submits an application.
    """

    started_at = (
        _utc_now_iso()
    )

    started_clock = (
        monotonic_fn()
    )

    if delay_seconds < 0:
        raise ValueError(
            "delay_seconds must be >= 0."
        )

    repository = (
        repository
        or JobRepository()
    )

    candidates = (
        repository
        .list_browser_queue_candidates(
            limit=limit,
            include_in_progress=(
                include_in_progress
            ),
            board_token=(
                board_token
            ),
            order=order,
        )
    )

    queue_run_id = (
        run_id
        or _utc_run_id()
    )

    queue_root = (
        Path(
            artifacts_dir
        )
        / queue_run_id
    )

    results = []

    for index, candidate in enumerate(
        candidates
    ):

        row = {
            "job_id": (
                candidate.get(
                    "job_id"
                )
            ),
            "application_id": (
                candidate.get(
                    "application_id"
                )
            ),
            "board_token": (
                candidate.get(
                    "board_token"
                )
            ),
            "greenhouse_job_id": str(
                candidate.get(
                    "greenhouse_job_id"
                )
                or ""
            ),
            "company": (
                candidate.get(
                    "company"
                )
            ),
            "title": (
                candidate.get(
                    "title"
                )
            ),
            "matcher_route": (
                candidate.get(
                    "route"
                )
            ),
            "selected_resume": (
                Path(
                    str(
                        candidate.get(
                            "selected_resume_file"
                        )
                        or ""
                    )
                )
                .name
            ),
            "queue_status": (
                "STARTED"
            ),
            "outcome": None,
            "challenge_detected": False,
            "ready_count": 0,
            "required_human_count": 0,
            "browser_modified": False,
            "persisted": False,
            "application_status_after": (
                candidate.get(
                    "application_status"
                )
            ),
            "submit_clicked_by_agent": False,
            "application_submitted": False,
            "error_type": None,
            "error": None,
        }

        try:

            orchestration = (
                orchestrate_fn(
                    board_token=(
                        candidate[
                            "board_token"
                        ]
                    ),
                    greenhouse_job_id=(
                        candidate[
                            "greenhouse_job_id"
                        ]
                    ),
                    profile=profile,
                    resume_dir=(
                        resume_dir
                    ),
                    artifacts_dir=(
                        queue_root
                        / "jobs"
                    ),
                    headless=headless,
                    persist=persist,
                    repository=repository,
                )
            )

            row.update(
                {
                    "queue_status": (
                        "COMPLETED"
                    ),
                    "outcome": (
                        orchestration.get(
                            "outcome"
                        )
                    ),
                    "challenge_detected": (
                        bool(
                            orchestration.get(
                                "challenge_detected"
                            )
                        )
                    ),
                    "ready_count": int(
                        orchestration.get(
                            "ready_count"
                        )
                        or 0
                    ),
                    "required_human_count": int(
                        orchestration.get(
                            "required_human_count"
                        )
                        or 0
                    ),
                    "browser_modified": bool(
                        orchestration.get(
                            "browser_modified"
                        )
                    ),
                    "persisted": bool(
                        orchestration.get(
                            "persisted"
                        )
                    ),
                    "submit_clicked_by_agent": False,
                    "application_submitted": False,
                }
            )

            if (
                persist
                and orchestration.get(
                    "outcome"
                )
                == "READY_NO_SUBMIT"
            ):

                repository.mark_browser_ready_no_submit(
                    job_id=(
                        candidate[
                            "job_id"
                        ]
                    )
                )

                row[
                    "application_status_after"
                ] = "IN_PROGRESS"

        except RuntimeError as exc:

            row[
                "queue_status"
            ] = "BLOCKED"

            row[
                "error_type"
            ] = type(
                exc
            ).__name__

            row[
                "error"
            ] = str(
                exc
            )

        except Exception as exc:

            # Per-job isolation: unexpected runtime failures never
            # cause the queue to act on another job's state.
            row[
                "queue_status"
            ] = "ERROR"

            row[
                "error_type"
            ] = type(
                exc
            ).__name__

            row[
                "error"
            ] = str(
                exc
            )

        results.append(
            row
        )

        if (
            index
            < len(
                candidates
            )
            - 1
            and delay_seconds
            > 0
        ):

            sleep_fn(
                delay_seconds
            )

    summary = {
        "selected": len(
            candidates
        ),
        "completed": sum(
            1
            for row in results
            if row[
                "queue_status"
            ]
            == "COMPLETED"
        ),
        "needs_assistance": sum(
            1
            for row in results
            if row.get(
                "outcome"
            )
            == "NEEDS_ASSISTANCE"
        ),
        "ready_no_submit": sum(
            1
            for row in results
            if row.get(
                "outcome"
            )
            == "READY_NO_SUBMIT"
        ),
        "blocked": sum(
            1
            for row in results
            if row[
                "queue_status"
            ]
            == "BLOCKED"
        ),
        "errors": sum(
            1
            for row in results
            if row[
                "queue_status"
            ]
            == "ERROR"
        ),
        "challenge_count": sum(
            1
            for row in results
            if row.get(
                "challenge_detected"
            )
        ),
        "browser_modified_count": sum(
            1
            for row in results
            if row.get(
                "browser_modified"
            )
        ),
        "submitted": 0,
    }

    completed_at = (
        _utc_now_iso()
    )

    total_seconds = round(
        max(
            0.0,
            (
                monotonic_fn()
                - started_clock
            ),
        ),
        3,
    )

    report = {
        "queue_runner_version": 1,
        "run_id": queue_run_id,
        "started_at": (
            started_at
        ),
        "completed_at": (
            completed_at
        ),
        "total_seconds": (
            total_seconds
        ),
        "persist": bool(
            persist
        ),
        "history_persisted": False,
        "history_id": None,
        "history_error": None,
        "limit": limit,
        "include_in_progress": bool(
            include_in_progress
        ),
        "board_token_filter": (
            board_token
        ),
        "order": order,
        "delay_seconds": (
            delay_seconds
        ),
        "summary": summary,
        "results": results,
        "application_submitted": False,
        "submit_clicked_by_agent": False,
    }

    if persist:

        try:

            history_id = (
                repository
                .sync_browser_queue_run_history(
                    report
                )
            )

            report[
                "history_persisted"
            ] = True

            report[
                "history_id"
            ] = str(
                history_id
            )

        except Exception as exc:

            report[
                "history_error"
            ] = (
                f"{type(exc).__name__}: "
                f"{str(exc)[:300]}"
            )

    report_path = (
        queue_root
        / "queue_report.json"
    )

    _write_json(
        report_path,
        report,
    )

    report[
        "report_path"
    ] = str(
        report_path
    )

    return report
