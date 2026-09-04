from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import (
    urlencode,
    urlparse,
)

from src.browser.assistance_handoff import (
    ROUTE_AGENT_CONTINUE,
    ROUTE_NEEDS_ASSISTANCE,
    build_assistance_handoff,
    render_handoff_markdown,
)
from src.browser.browser_agent import (
    inspect_application,
)
from src.browser.safe_form_filler import (
    safe_fill_application,
)
from src.database.repository import (
    JobRepository,
)
from src.profile.applicant_profile import (
    ApplicantProfile,
)


ALLOWED_GREENHOUSE_HOSTS = {
    "job-boards.greenhouse.io",
    "boards.greenhouse.io",
}


def _is_greenhouse_url(
    value: str | None,
) -> bool:
    if not value:
        return False

    try:
        parsed = urlparse(
            value
        )
    except Exception:
        return False

    return (
        parsed.scheme
        == "https"
        and parsed.hostname
        in ALLOWED_GREENHOUSE_HOSTS
    )


def _greenhouse_application_url(
    *,
    board_token: str,
    greenhouse_job_id,
) -> str:
    """
    Build a Greenhouse-hosted application form URL.

    Some Greenhouse customers store a company careers URL in jobs.url.
    Browser Orchestrator V1.1.1 does not whitelist company domains; it
    derives Greenhouse's own embedded application endpoint instead.
    """

    board = str(
        board_token
        or ""
    ).strip()

    job_token = str(
        greenhouse_job_id
        or ""
    ).strip()

    if not re.fullmatch(
        r"[A-Za-z0-9_-]+",
        board,
    ):
        raise RuntimeError(
            "Browser orchestration blocked: "
            "invalid Greenhouse board token."
        )

    if not job_token.isdigit():
        raise RuntimeError(
            "Browser orchestration blocked: "
            "invalid Greenhouse job id."
        )

    query = urlencode(
        {
            "for": board,
            "token": job_token,
        }
    )

    return (
        "https://job-boards.greenhouse.io/"
        f"embed/job_app?{query}"
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


def _browser_artifact_paths(
    *,
    artifacts_dir: str | Path,
    board_token: str,
    greenhouse_job_id,
) -> dict[str, Path]:
    root = (
        Path(
            artifacts_dir
        )
        / (
            f"{board_token}_"
            f"{greenhouse_job_id}"
        )
    )

    return {
        "root": root,
        "inspection": (
            root
            / "inspection.json"
        ),
        "fill": (
            root
            / "fill.json"
        ),
        "handoff": (
            root
            / "handoff.json"
        ),
        "handoff_markdown": (
            root
            / "handoff.md"
        ),
        "orchestrator": (
            root
            / "orchestrator.json"
        ),
    }


def _apply_external_safety_reason(
    *,
    handoff: dict,
    reason: str,
) -> dict:
    """
    Fail-safe override for an orchestration-level block
    discovered after read-only inspection but before filling.
    """

    output = dict(
        handoff
    )

    reasons = list(
        output.get(
            "route_reasons"
        )
        or []
    )

    if reason not in reasons:
        reasons.append(
            reason
        )

    output[
        "route"
    ] = ROUTE_NEEDS_ASSISTANCE

    output[
        "route_reasons"
    ] = reasons

    return output


def orchestrate_browser_application(
    *,
    board_token: str,
    greenhouse_job_id,
    profile: ApplicantProfile,
    resume_dir: str | Path = "resumes",
    artifacts_dir: str | Path = "browser_runs/orchestrator",
    headless: bool = True,
    persist: bool = True,
    repository: JobRepository | None = None,
    inspect_fn=inspect_application,
    fill_fn=safe_fill_application,
) -> dict:
    """
    Browser Orchestrator V1.

    Safe sequence:
      1. resolve tracked job
      2. fail-closed production route/application checks
      3. resolve matcher-selected resume
      4. read-only live inspection
      5. re-check route before any mutation
      6. safe dry-run fill (CAPTCHA hard gate)
      7. generate redacted assistance handoff
      8. persist browser assistance/continuation

    There is intentionally NO submission call or submit option.
    """

    repository = (
        repository
        or JobRepository()
    )

    job_id = (
        repository.find_job_id(
            board_token=(
                board_token
            ),
            greenhouse_job_id=(
                greenhouse_job_id
            ),
        )
    )

    if not job_id:
        raise RuntimeError(
            "Browser orchestration blocked: "
            "matching tracked job was not found."
        )

    context = (
        repository
        .assert_browser_execution_allowed(
            job_id=(
                job_id
            ),
        )
    )

    job = (
        context[
            "job"
        ]
    )

    evaluation = (
        context[
            "evaluation"
        ]
    )

    stored_job_url = (
        job.get(
            "url"
        )
    )

    application_url = (
        _greenhouse_application_url(
            board_token=(
                job.get(
                    "board_token"
                )
                or board_token
            ),
            greenhouse_job_id=(
                job.get(
                    "greenhouse_job_id"
                )
                or greenhouse_job_id
            ),
        )
    )

    if not _is_greenhouse_url(
        application_url
    ):
        raise RuntimeError(
            "Browser orchestration blocked: "
            "canonical application URL is not on "
            "an approved Greenhouse HTTPS host."
        )

    selected_resume_file = (
        Path(
            str(
                evaluation[
                    "selected_resume_file"
                ]
            )
        )
        .name
    )

    resume_path = (
        Path(
            resume_dir
        )
        / selected_resume_file
    )

    if not resume_path.is_file():
        raise RuntimeError(
            "Browser orchestration blocked: "
            "matcher-selected resume file does "
            f"not exist: {resume_path}"
        )

    paths = (
        _browser_artifact_paths(
            artifacts_dir=(
                artifacts_dir
            ),
            board_token=(
                board_token
            ),
            greenhouse_job_id=(
                greenhouse_job_id
            ),
        )
    )

    inspection = inspect_fn(
        url=(
            application_url
        ),
        headless=(
            headless
        ),
    )

    _write_json(
        paths[
            "inspection"
        ],
        inspection,
    )

    final_url = (
        inspection.get(
            "final_url"
        )
        or application_url
    )

    # We inspect read-only first. If Greenhouse redirects
    # somewhere outside the approved ATS hosts, do not fill.
    if not _is_greenhouse_url(
        final_url
    ):
        handoff = (
            build_assistance_handoff(
                inspection=(
                    inspection
                ),
                profile=(
                    profile
                ),
                resume_path=(
                    resume_path
                ),
                fill_report=None,
                company=(
                    job.get(
                        "company"
                    )
                ),
                job_title=(
                    job.get(
                        "title"
                    )
                ),
            )
        )

        handoff = (
            _apply_external_safety_reason(
                handoff=(
                    handoff
                ),
                reason=(
                    "Greenhouse page redirected "
                    "outside the approved ATS hosts; "
                    "browser mutation was skipped."
                ),
            )
        )

        fill_report = {
            "requested_url": (
                application_url
            ),
            "final_url": (
                final_url
            ),
            "fill_results": [],
            "fill_summary": {
                "tasks_attempted": 0,
                "filled": 0,
                "fill_failed": 0,
                "submit_attempts_blocked": 0,
                "submit_clicked_by_agent": False,
                "application_submitted": False,
                "browser_modified": False,
                "page_challenge_detected": False,
                "page_challenge_reasons": [],
                "mutation_blocked_by_challenge": False,
                "nonready_mutation_detected": False,
                "nonready_mutation_reason": "",
                "orchestrator_blocked_before_fill": True,
            },
        }

    else:
        # Route/application state can change between
        # inspection and mutation. Re-check immediately
        # before opening the mutating browser session.
        repository.assert_browser_execution_allowed(
            job_id=(
                job_id
            ),
        )

        fill_report = fill_fn(
            url=(
                final_url
            ),
            profile=(
                profile
            ),
            resume_path=(
                resume_path
            ),
            headless=(
                headless
            ),
        )

        fill_summary = (
            fill_report.get(
                "fill_summary"
            )
            or {}
        )

        if (
            fill_summary.get(
                "submit_clicked_by_agent"
            )
            or fill_summary.get(
                "application_submitted"
            )
        ):
            raise RuntimeError(
                "Browser safety invariant failed: "
                "a submission state was reported."
            )

        handoff = (
            build_assistance_handoff(
                inspection=(
                    inspection
                ),
                profile=(
                    profile
                ),
                resume_path=(
                    resume_path
                ),
                fill_report=(
                    fill_report
                ),
                company=(
                    job.get(
                        "company"
                    )
                ),
                job_title=(
                    job.get(
                        "title"
                    )
                ),
            )
        )

    _write_json(
        paths[
            "fill"
        ],
        fill_report,
    )

    _write_json(
        paths[
            "handoff"
        ],
        handoff,
    )

    paths[
        "handoff_markdown"
    ].write_text(
        render_handoff_markdown(
            handoff
        ),
        encoding="utf-8",
    )

    application_id = (
        context[
            "application"
        ][
            "id"
        ]
    )

    if persist:
        # Repository repeats the AGENT_APPLY route guard,
        # protecting against a final race before the write.
        application_id = (
            repository
            .sync_browser_assistance_handoff(
                job_id=(
                    job_id
                ),
                handoff=(
                    handoff
                ),
            )
        )

    fill_summary = (
        fill_report.get(
            "fill_summary"
        )
        or {}
    )

    handoff_summary = (
        handoff.get(
            "summary"
        )
        or {}
    )

    outcome = (
        "NEEDS_ASSISTANCE"
        if handoff.get(
            "route"
        )
        == ROUTE_NEEDS_ASSISTANCE
        else "READY_NO_SUBMIT"
    )

    result = {
        "orchestrator_version": 1.1,
        "job_id": (
            job_id
        ),
        "application_id": (
            application_id
        ),
        "board_token": (
            board_token
        ),
        "greenhouse_job_id": str(
            greenhouse_job_id
        ),
        "company": (
            job.get(
                "company"
            )
        ),
        "job_title": (
            job.get(
                "title"
            )
        ),
        "stored_job_url_host": (
            urlparse(
                stored_job_url
                or ""
            ).hostname
            or ""
        ),
        "application_url_host": (
            urlparse(
                application_url
            ).hostname
            or ""
        ),
        "matcher_route": (
            evaluation.get(
                "route"
            )
        ),
        "selected_resume": (
            selected_resume_file
        ),
        "handoff_route": (
            handoff.get(
                "route"
            )
        ),
        "outcome": (
            outcome
        ),
        "challenge_detected": bool(
            handoff_summary.get(
                "challenge_detected"
            )
        ),
        "ready_count": int(
            handoff_summary.get(
                "ready_count"
            )
            or 0
        ),
        "required_human_count": int(
            handoff_summary.get(
                "required_human_count"
            )
            or 0
        ),
        "fill_tasks_attempted": int(
            fill_summary.get(
                "tasks_attempted"
            )
            or 0
        ),
        "filled": int(
            fill_summary.get(
                "filled"
            )
            or 0
        ),
        "fill_failed": int(
            fill_summary.get(
                "fill_failed"
            )
            or 0
        ),
        "browser_modified": bool(
            fill_summary.get(
                "browser_modified"
            )
        ),
        "persisted": bool(
            persist
        ),
        "submit_clicked_by_agent": False,
        "application_submitted": False,
        "artifacts": {
            key: str(
                value
            )
            for key, value
            in paths.items()
            if key
            != "root"
        },
    }

    _write_json(
        paths[
            "orchestrator"
        ],
        result,
    )

    return result
