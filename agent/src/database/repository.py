from pathlib import Path

from datetime import (
    datetime,
    timezone,
)

from src.database.supabase_client import (
    get_owner_id,
    get_supabase_client,
)


# ============================================================
# TIME
# ============================================================

def utc_now() -> str:
    """
    Return current UTC timestamp in ISO format.
    """

    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )


# ============================================================
# JOB LIFECYCLE HELPERS
# ============================================================

def normalize_greenhouse_job_ids(
    values,
) -> set[str]:
    """
    Normalize Greenhouse job IDs for reliable comparison.
    """

    normalized = set()

    for value in (
        values
        or []
    ):

        if value is None:

            continue

        text = str(
            value
        ).strip()

        if text:

            normalized.add(
                text
            )

    return normalized


def find_stale_job_rows(
    tracked_rows: list[dict],
    live_greenhouse_job_ids,
) -> list[dict]:
    """
    Return active tracked jobs whose Greenhouse IDs are no
    longer present in the latest successful board fetch.

    An empty live-ID set intentionally returns no stale jobs.
    This is a safety guard against mass deactivation when a
    board unexpectedly returns an empty response.
    """

    live_ids = (
        normalize_greenhouse_job_ids(
            live_greenhouse_job_ids
        )
    )

    if not live_ids:

        return []

    stale_rows = []

    for row in (
        tracked_rows
        or []
    ):

        if row.get(
            "is_active",
            True,
        ) is False:

            continue

        greenhouse_job_id = (
            str(
                row.get(
                    "greenhouse_job_id",
                    "",
                )
            )
            .strip()
        )

        if (
            greenhouse_job_id
            and greenhouse_job_id
            not in live_ids
        ):

            stale_rows.append(
                row
            )

    return stale_rows



BROWSER_HANDOFF_VERSION = 1

BROWSER_ROUTE_NEEDS_ASSISTANCE = (
    "NEEDS_ASSISTANCE"
)

BROWSER_ROUTE_AGENT_CONTINUE = (
    "AGENT_CONTINUE"
)

BROWSER_POLICY_ANSWER_KEYS = {
    "WORK_AUTHORIZED_US",
    "SPONSORSHIP_NOW",
    "SPONSORSHIP_FUTURE",
    "SPONSORSHIP_NOW_OR_FUTURE",
    "WORK_AUTH_WITHOUT_SPONSORSHIP_NOW",
    "WORK_AUTH_WITHOUT_SPONSORSHIP_FUTURE",
}


def _safe_text(
    value,
    *,
    max_length: int = 4000,
):
    if value is None:

        return None

    text = str(
        value
    ).strip()

    if not text:

        return None

    return text[
        :max_length
    ]


def _safe_string_list(
    values,
    *,
    max_items: int = 50,
    max_length: int = 1000,
) -> list[str]:
    output = []

    for value in (
        values
        or []
    )[
        :max_items
    ]:

        text = _safe_text(
            value,
            max_length=(
                max_length
            ),
        )

        if (
            text
            and text
            not in output
        ):

            output.append(
                text
            )

    return output


def _safe_handoff_item(
    item,
) -> dict:
    if not isinstance(
        item,
        dict,
    ):

        item = {}

    answer_key = (
        _safe_text(
            item.get(
                "answer_key"
            ),
            max_length=(
                120
            ),
        )
    )

    display_answer = None

    if (
        answer_key
        in BROWSER_POLICY_ANSWER_KEYS
    ):

        raw_display = (
            _safe_text(
                item.get(
                    "display_answer"
                ),
                max_length=(
                    32
                ),
            )
        )

        if raw_display in {
            "Yes",
            "No",
            "True",
            "False",
        }:

            display_answer = (
                raw_display
            )

    return {
        "label": _safe_text(
            item.get(
                "label"
            ),
            max_length=(
                1500
            ),
        ),

        "category": _safe_text(
            item.get(
                "category"
            ),
            max_length=(
                120
            ),
        ),

        "required": bool(
            item.get(
                "required"
            )
        ),

        "status": _safe_text(
            item.get(
                "status"
            ),
            max_length=(
                120
            ),
        ),

        "source": _safe_text(
            item.get(
                "source"
            ),
            max_length=(
                120
            ),
        ),

        "answer_key": (
            answer_key
        ),

        # Defensive redaction:
        # only fixed policy Yes/No-style
        # answers may persist.
        "display_answer": (
            display_answer
        ),

        "reason": _safe_text(
            item.get(
                "reason"
            ),
            max_length=(
                2000
            ),
        ),
    }


def sanitize_browser_handoff(
    handoff,
) -> dict:
    """
    Return the database-safe subset of a browser handoff.

    Safety rules:
        - only handoff packet V1 is accepted
        - local resume paths become basenames
        - profile values are never persisted
        - display_answer is retained only for approved
          work-authorization/sponsorship policy keys
        - unknown top-level keys are discarded
        - summary counts are recomputed from sanitized items
    """

    if not isinstance(
        handoff,
        dict,
    ):

        raise ValueError(
            "Browser handoff must be a dictionary."
        )

    packet_version = (
        handoff.get(
            "packet_version"
        )
    )

    if (
        packet_version
        != BROWSER_HANDOFF_VERSION
    ):

        raise ValueError(
            "Unsupported browser handoff "
            f"packet_version: {packet_version!r}"
        )

    route = (
        _safe_text(
            handoff.get(
                "route"
            ),
            max_length=(
                80
            ),
        )
    )

    if route not in {
        BROWSER_ROUTE_NEEDS_ASSISTANCE,
        BROWSER_ROUTE_AGENT_CONTINUE,
    }:

        raise ValueError(
            "Unsupported browser handoff "
            f"route: {route!r}"
        )

    selected_resume = (
        _safe_text(
            handoff.get(
                "selected_resume"
            ),
            max_length=(
                500
            ),
        )
    )

    if selected_resume:

        selected_resume = (
            Path(
                selected_resume
            )
            .name
        )

    challenge = (
        handoff.get(
            "challenge"
        )
        or {}
    )

    browser_safety = (
        handoff.get(
            "browser_safety"
        )
        or {}
    )

    deterministic_ready = [
        _safe_handoff_item(
            item
        )
        for item in (
            handoff.get(
                "deterministic_ready"
            )
            or []
        )[
            :100
        ]
    ]

    human_assistance = [
        _safe_handoff_item(
            item
        )
        for item in (
            handoff.get(
                "human_assistance"
            )
            or []
        )[
            :100
        ]
    ]

    required_human_count = sum(
        1
        for item in (
            human_assistance
        )
        if item.get(
            "required"
        )
    )

    incoming_summary = (
        handoff.get(
            "summary"
        )
        or {}
    )

    policy_mismatches = int(
        incoming_summary.get(
            "policy_mismatches"
        )
        or 0
    )

    missing_resume = int(
        incoming_summary.get(
            "missing_resume"
        )
        or 0
    )

    challenge_detected = bool(
        challenge.get(
            "detected"
        )
    )

    safe_packet = {
        "packet_version": (
            BROWSER_HANDOFF_VERSION
        ),

        "company": _safe_text(
            handoff.get(
                "company"
            ),
            max_length=(
                500
            ),
        ),

        "job_title": _safe_text(
            handoff.get(
                "job_title"
            ),
            max_length=(
                1000
            ),
        ),

        "requested_url": _safe_text(
            handoff.get(
                "requested_url"
            ),
            max_length=(
                3000
            ),
        ),

        "page_title": _safe_text(
            handoff.get(
                "page_title"
            ),
            max_length=(
                1500
            ),
        ),

        "selected_resume": (
            selected_resume
        ),

        "route": (
            route
        ),

        "route_reasons": (
            _safe_string_list(
                handoff.get(
                    "route_reasons"
                ),
                max_items=(
                    20
                ),
                max_length=(
                    1000
                ),
            )
        ),

        "challenge": {
            "detected": (
                challenge_detected
            ),

            "reasons": (
                _safe_string_list(
                    challenge.get(
                        "reasons"
                    ),
                    max_items=(
                        20
                    ),
                    max_length=(
                        1000
                    ),
                )
            ),
        },

        "browser_safety": {
            "application_submitted": (
                bool(
                    browser_safety.get(
                        "application_submitted"
                    )
                )
            ),

            "submit_clicked_by_agent": (
                bool(
                    browser_safety.get(
                        "submit_clicked_by_agent"
                    )
                )
            ),

            "nonready_mutation_detected": (
                bool(
                    browser_safety.get(
                        "nonready_mutation_detected"
                    )
                )
            ),

            "nonready_mutation_reason": (
                _safe_text(
                    browser_safety.get(
                        "nonready_mutation_reason"
                    ),
                    max_length=(
                        2000
                    ),
                )
            ),
        },

        "deterministic_ready": (
            deterministic_ready
        ),

        "human_assistance": (
            human_assistance
        ),

        "summary": {
            "ready_count": len(
                deterministic_ready
            ),

            "human_assistance_count": len(
                human_assistance
            ),

            "required_human_count": (
                required_human_count
            ),

            "challenge_detected": (
                challenge_detected
            ),

            "policy_mismatches": (
                max(
                    policy_mismatches,
                    0,
                )
            ),

            "missing_resume": (
                max(
                    missing_resume,
                    0,
                )
            ),
        },
    }

    return safe_packet


def build_browser_assistance_reason(
    handoff: dict,
) -> str:
    """
    Build a compact application-level reason.

    The structured handoff remains in assistance_requests.handoff.
    """

    safe_packet = (
        sanitize_browser_handoff(
            handoff
        )
    )

    summary = (
        safe_packet[
            "summary"
        ]
    )

    browser_safety = (
        safe_packet[
            "browser_safety"
        ]
    )

    tokens = []

    if summary[
        "challenge_detected"
    ]:

        tokens.append(
            "CAPTCHA"
        )

    required_count = (
        summary[
            "required_human_count"
        ]
    )

    if required_count:

        tokens.append(
            "REQUIRED_QUESTIONS="
            f"{required_count}"
        )

    if summary[
        "policy_mismatches"
    ]:

        tokens.append(
            "POLICY_MISMATCH"
        )

    if summary[
        "missing_resume"
    ]:

        tokens.append(
            "MISSING_RESUME"
        )

    if browser_safety[
        "nonready_mutation_detected"
    ]:

        tokens.append(
            "SAFETY_VIOLATION"
        )

    if not tokens:

        tokens.append(
            "HUMAN_REVIEW"
        )

    return (
        "BROWSER: "
        + " + ".join(
            tokens
        )
    )


def build_browser_assistance_question(
    handoff: dict,
) -> str:
    safe_packet = (
        sanitize_browser_handoff(
            handoff
        )
    )

    summary = (
        safe_packet[
            "summary"
        ]
    )

    parts = []

    if summary[
        "challenge_detected"
    ]:

        parts.append(
            "CAPTCHA detected"
        )

    required_count = (
        summary[
            "required_human_count"
        ]
    )

    if required_count:

        parts.append(
            f"{required_count} required "
            "field(s) need review"
        )

    ready_count = (
        summary[
            "ready_count"
        ]
    )

    if ready_count:

        parts.append(
            f"{ready_count} deterministic "
            "field(s) are ready"
        )

    if not parts:

        parts.append(
            "browser handoff needs review"
        )

    return (
        "Browser application handoff: "
        + "; ".join(
            parts
        )
        + "."
    )


# ============================================================
# REPOSITORY
# ============================================================


BROWSER_QUEUE_HISTORY_VERSION = 1

_BROWSER_QUEUE_STATUSES = {
    "COMPLETED",
    "BLOCKED",
    "ERROR",
}

_BROWSER_QUEUE_OUTCOMES = {
    "NEEDS_ASSISTANCE",
    "READY_NO_SUBMIT",
}

_BROWSER_QUEUE_ORDERS = {
    "oldest",
    "newest",
    "fit",
}


def _safe_nonnegative_int(
    value,
    *,
    default: int = 0,
) -> int:
    try:
        parsed = int(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return default

    return max(
        0,
        parsed,
    )


def _safe_nonnegative_float(
    value,
    *,
    default: float = 0.0,
) -> float:
    try:
        parsed = float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return default

    if parsed < 0:
        return default

    return round(
        parsed,
        3,
    )


def _sanitize_browser_queue_result(
    row,
) -> dict:
    """
    Keep only non-PII operational fields for one queue result.
    """

    if not isinstance(
        row,
        dict,
    ):
        row = {}

    queue_status = (
        _safe_text(
            row.get(
                "queue_status"
            ),
            max_length=40,
        )
        or "ERROR"
    )

    if queue_status not in (
        _BROWSER_QUEUE_STATUSES
    ):
        queue_status = "ERROR"

    outcome = _safe_text(
        row.get(
            "outcome"
        ),
        max_length=40,
    )

    if outcome not in (
        _BROWSER_QUEUE_OUTCOMES
    ):
        outcome = None

    return {
        "board_token": (
            _safe_text(
                row.get(
                    "board_token"
                ),
                max_length=120,
            )
        ),
        "greenhouse_job_id": (
            _safe_text(
                row.get(
                    "greenhouse_job_id"
                ),
                max_length=80,
            )
        ),
        "company": (
            _safe_text(
                row.get(
                    "company"
                ),
                max_length=300,
            )
        ),
        "title": (
            _safe_text(
                row.get(
                    "title"
                ),
                max_length=500,
            )
        ),
        "queue_status": (
            queue_status
        ),
        "outcome": (
            outcome
        ),
        "challenge_detected": (
            bool(
                row.get(
                    "challenge_detected"
                )
            )
        ),
        "ready_count": (
            _safe_nonnegative_int(
                row.get(
                    "ready_count"
                )
            )
        ),
        "required_human_count": (
            _safe_nonnegative_int(
                row.get(
                    "required_human_count"
                )
            )
        ),
        "browser_modified": (
            bool(
                row.get(
                    "browser_modified"
                )
            )
        ),
        "application_status_after": (
            _safe_text(
                row.get(
                    "application_status_after"
                ),
                max_length=80,
            )
        ),
        "error_type": (
            _safe_text(
                row.get(
                    "error_type"
                ),
                max_length=160,
            )
        ),
        "submit_clicked_by_agent": False,
        "application_submitted": False,
    }


def sanitize_browser_queue_history_report(
    report,
) -> dict:
    """
    Convert a local Browser Queue Runner report into a strict,
    redacted Supabase payload.

    Applicant profile values, resume contents, local file paths,
    arbitrary exception messages, and browser artifacts are not kept.
    """

    if not isinstance(
        report,
        dict,
    ):
        raise RuntimeError(
            "Browser queue history blocked: invalid report."
        )

    if (
        bool(
            report.get(
                "submit_clicked_by_agent"
            )
        )
        or bool(
            report.get(
                "application_submitted"
            )
        )
    ):
        raise RuntimeError(
            "Browser queue history blocked: "
            "submission invariant violated."
        )

    run_key = (
        _safe_text(
            report.get(
                "run_id"
            ),
            max_length=120,
        )
    )

    if not run_key:
        raise RuntimeError(
            "Browser queue history blocked: run_id missing."
        )

    order = (
        _safe_text(
            report.get(
                "order"
            ),
            max_length=40,
        )
        or "oldest"
    )

    if order not in (
        _BROWSER_QUEUE_ORDERS
    ):
        raise RuntimeError(
            "Browser queue history blocked: "
            "invalid queue order."
        )

    sanitized_results = [
        _sanitize_browser_queue_result(
            row
        )
        for row in (
            report.get(
                "results"
            )
            or []
        )[
            :50
        ]
    ]

    selected_count = len(
        sanitized_results
    )

    completed_count = sum(
        1
        for row in (
            sanitized_results
        )
        if row[
            "queue_status"
        ]
        == "COMPLETED"
    )

    needs_assistance_count = sum(
        1
        for row in (
            sanitized_results
        )
        if row.get(
            "outcome"
        )
        == "NEEDS_ASSISTANCE"
    )

    ready_no_submit_count = sum(
        1
        for row in (
            sanitized_results
        )
        if row.get(
            "outcome"
        )
        == "READY_NO_SUBMIT"
    )

    blocked_count = sum(
        1
        for row in (
            sanitized_results
        )
        if row[
            "queue_status"
        ]
        == "BLOCKED"
    )

    error_count = sum(
        1
        for row in (
            sanitized_results
        )
        if row[
            "queue_status"
        ]
        == "ERROR"
    )

    challenge_count = sum(
        1
        for row in (
            sanitized_results
        )
        if row[
            "challenge_detected"
        ]
    )

    browser_modified_count = sum(
        1
        for row in (
            sanitized_results
        )
        if row[
            "browser_modified"
        ]
    )

    return {
        "run_key": (
            run_key
        ),
        "runner_version": (
            BROWSER_QUEUE_HISTORY_VERSION
        ),
        "status": (
            "COMPLETED"
        ),
        "persist_handoffs": (
            bool(
                report.get(
                    "persist"
                )
            )
        ),
        "board_token_filter": (
            _safe_text(
                report.get(
                    "board_token_filter"
                ),
                max_length=120,
            )
        ),
        "queue_order": (
            order
        ),
        "queue_limit": (
            min(
                50,
                max(
                    1,
                    _safe_nonnegative_int(
                        report.get(
                            "limit"
                        ),
                        default=1,
                    ),
                ),
            )
        ),
        "include_in_progress": (
            bool(
                report.get(
                    "include_in_progress"
                )
            )
        ),
        "started_at": (
            _safe_text(
                report.get(
                    "started_at"
                ),
                max_length=80,
            )
        ),
        "completed_at": (
            _safe_text(
                report.get(
                    "completed_at"
                ),
                max_length=80,
            )
        ),
        "total_seconds": (
            _safe_nonnegative_float(
                report.get(
                    "total_seconds"
                )
            )
        ),
        "selected_count": (
            selected_count
        ),
        "completed_count": (
            completed_count
        ),
        "needs_assistance_count": (
            needs_assistance_count
        ),
        "ready_no_submit_count": (
            ready_no_submit_count
        ),
        "blocked_count": (
            blocked_count
        ),
        "error_count": (
            error_count
        ),
        "challenge_count": (
            challenge_count
        ),
        "browser_modified_count": (
            browser_modified_count
        ),
        "submitted_count": 0,
        "submit_clicked_by_agent": False,
        "application_submitted": False,
        "results": (
            sanitized_results
        ),
        "updated_at": (
            utc_now()
        ),
    }


class JobRepository:
    """
    Database layer for the Greenhouse Job Agent.

    Responsibilities:
        - agent run history
        - job persistence
        - evaluation history
        - application tracking
        - eligibility assistance
    """

    def __init__(self):

        self.client = (
            get_supabase_client()
        )

        self.owner_id = (
            get_owner_id()
        )

    # ========================================================
    # AGENT RUNS
    # ========================================================

    def create_agent_run(
        self,
        board_token: str,
    ) -> str:

        payload = {
            "owner_id": (
                self.owner_id
            ),

            "board_token": (
                board_token
            ),
        }

        response = (
            self.client
            .table(
                "agent_runs"
            )
            .insert(
                payload
            )
            .execute()
        )

        if not response.data:

            raise RuntimeError(
                "Failed to create agent run."
            )

        return (
            response.data[0][
                "id"
            ]
        )

    def complete_agent_run(
        self,
        run_id: str,
        *,
        jobs_discovered: int,
        target_role_jobs: int,
        us_compatible_jobs: int,
        jobs_eligible: int,
        manual_priority_count: int,
        agent_apply_count: int,
        experience_rejected_count: int,
        unknown_location_count: int,
        fetch_seconds: float,
        filtering_seconds: float,
        resume_cache_seconds: float,
        scoring_seconds: float,
        total_seconds: float,
    ) -> None:

        payload = {
            "completed_at": (
                utc_now()
            ),

            "jobs_discovered": (
                jobs_discovered
            ),

            "target_role_jobs": (
                target_role_jobs
            ),

            "us_compatible_jobs": (
                us_compatible_jobs
            ),

            "jobs_eligible": (
                jobs_eligible
            ),

            "manual_priority_count": (
                manual_priority_count
            ),

            "agent_apply_count": (
                agent_apply_count
            ),

            "experience_rejected_count": (
                experience_rejected_count
            ),

            "unknown_location_count": (
                unknown_location_count
            ),

            "fetch_seconds": round(
                fetch_seconds,
                3,
            ),

            "filtering_seconds": round(
                filtering_seconds,
                3,
            ),

            "resume_cache_seconds": round(
                resume_cache_seconds,
                3,
            ),

            "scoring_seconds": round(
                scoring_seconds,
                3,
            ),

            "total_seconds": round(
                total_seconds,
                3,
            ),
        }

        (
            self.client
            .table(
                "agent_runs"
            )
            .update(
                payload
            )
            .eq(
                "id",
                run_id,
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .execute()
        )

    # ========================================================
    # JOBS
    # ========================================================

    def upsert_job(
        self,
        *,
        greenhouse_job_id,
        board_token: str,
        company: str,
        title: str,
        location: str,
        url: str,
        detected_profile: str,
    ) -> str:

        now = (
            utc_now()
        )

        payload = {
            "owner_id": (
                self.owner_id
            ),

            "greenhouse_job_id": str(
                greenhouse_job_id
            ),

            "board_token": (
                board_token
            ),

            "company": (
                company
            ),

            "title": (
                title
            ),

            "location": (
                location
            ),

            "url": (
                url
            ),

            "detected_profile": (
                detected_profile
            ),

            "last_seen_at": (
                now
            ),

            "is_active": True,

            "updated_at": (
                now
            ),
        }

        response = (
            self.client
            .table(
                "jobs"
            )
            .upsert(
                payload,
                on_conflict=(
                    "owner_id,"
                    "board_token,"
                    "greenhouse_job_id"
                ),
            )
            .execute()
        )

        if response.data:

            return (
                response.data[0][
                    "id"
                ]
            )

        lookup = (
            self.client
            .table(
                "jobs"
            )
            .select(
                "id"
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "board_token",
                board_token,
            )
            .eq(
                "greenhouse_job_id",
                str(
                    greenhouse_job_id
                ),
            )
            .limit(
                1
            )
            .execute()
        )

        if not lookup.data:

            raise RuntimeError(
                "Job was upserted but could "
                "not be retrieved."
            )

        return (
            lookup.data[0][
                "id"
            ]
        )

    # ========================================================
    # JOB LIFECYCLE
    # ========================================================

    def sync_board_job_lifecycle(
        self,
        *,
        board_token: str,
        live_greenhouse_job_ids,
        dry_run: bool = False,
    ) -> dict:
        """
        Mark previously tracked jobs inactive when they are no
        longer present in a successful non-empty Greenhouse
        board fetch.

        Safety rules:
            - an empty live-ID set never deactivates anything
            - fetch failures are handled by main.py and never
              call this method
            - dry_run=True performs comparison only, no updates
            - historical evaluations/applications are preserved
            - if a job later reappears, upsert_job() sets
              is_active=True again automatically
        """

        live_ids = (
            normalize_greenhouse_job_ids(
                live_greenhouse_job_ids
            )
        )

        if not live_ids:

            return {
                "board_token": board_token,
                "live_count": 0,
                "tracked_active_count": 0,
                "stale_count": 0,
                "stale_jobs": [],
                "skipped": True,
                "reason": "EMPTY_LIVE_SET",
                "dry_run": dry_run,
            }

        response = (
            self.client
            .table(
                "jobs"
            )
            .select(
                (
                    "id,"
                    "greenhouse_job_id,"
                    "company,"
                    "title,"
                    "location,"
                    "url,"
                    "last_seen_at,"
                    "is_active"
                )
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "board_token",
                board_token,
            )
            .eq(
                "is_active",
                True,
            )
            .execute()
        )

        tracked_rows = (
            response.data
            or []
        )

        stale_rows = (
            find_stale_job_rows(
                tracked_rows,
                live_ids,
            )
        )

        if (
            stale_rows
            and not dry_run
        ):

            now = (
                utc_now()
            )

            stale_database_ids = [
                row[
                    "id"
                ]
                for row
                in stale_rows
            ]

            # Keep each update request comfortably small.
            batch_size = 100

            for start in range(
                0,
                len(
                    stale_database_ids
                ),
                batch_size,
            ):

                batch = (
                    stale_database_ids[
                        start:
                        start + batch_size
                    ]
                )

                (
                    self.client
                    .table(
                        "jobs"
                    )
                    .update(
                        {
                            "is_active": False,
                            "updated_at": now,
                        }
                    )
                    .eq(
                        "owner_id",
                        self.owner_id,
                    )
                    .eq(
                        "board_token",
                        board_token,
                    )
                    .in_(
                        "id",
                        batch,
                    )
                    .execute()
                )

        return {
            "board_token": board_token,
            "live_count": len(
                live_ids
            ),
            "tracked_active_count": len(
                tracked_rows
            ),
            "stale_count": len(
                stale_rows
            ),
            "stale_jobs": stale_rows,
            "skipped": False,
            "reason": None,
            "dry_run": dry_run,
        }

    # ========================================================
    # JOB EVALUATIONS
    # ========================================================

    def save_evaluation(
        self,
        *,
        run_id: str,
        job_id: str,
        best_match: dict,
    ) -> None:
        """
        Persist the selected resume and the complete V2.1
        job-fit explanation for this run/job pair.
        """

        payload = {
            "owner_id": (
                self.owner_id
            ),

            "run_id": (
                run_id
            ),

            "job_id": (
                job_id
            ),

            "score": (
                best_match[
                    "final_score"
                ]
            ),

            "selection_score": (
                best_match.get(
                    "selection_score"
                )
            ),

            "confidence": (
                best_match.get(
                    "confidence"
                )
            ),

            "route": (
                best_match[
                    "route"
                ]
            ),

            "selected_resume": (
                best_match[
                    "resume_name"
                ]
            ),

            "selected_resume_file": (
                best_match[
                    "filename"
                ]
            ),

            "role_score": (
                best_match[
                    "role_score"
                ]
            ),

            "required_score": (
                best_match[
                    "required_score"
                ]
            ),

            "preferred_score": (
                best_match[
                    "preferred_score"
                ]
            ),

            "semantic_score": (
                best_match[
                    "semantic_score"
                ]
            ),

            "experience_score": (
                best_match[
                    "experience_score"
                ]
            ),

            "explanation": (
                best_match.get(
                    "explanation",
                    {},
                )
                or {}
            ),
        }

        (
            self.client
            .table(
                "job_evaluations"
            )
            .upsert(
                payload,
                on_conflict=(
                    "run_id,job_id"
                ),
            )
            .execute()
        )

    # ========================================================
    # APPLICATION LOOKUP
    # ========================================================

    def _get_application(
        self,
        job_id: str,
    ):

        response = (
            self.client
            .table(
                "applications"
            )
            .select(
                (
                    "id,"
                    "status,"
                    "application_method,"
                    "needs_assistance,"
                    "assistance_reason"
                )
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "job_id",
                job_id,
            )
            .limit(
                1
            )
            .execute()
        )

        if response.data:

            return (
                response.data[0]
            )

        return None

    # ========================================================
    # NORMAL APPLICATION
    # ========================================================

    def ensure_application(
        self,
        *,
        job_id: str,
        route: str,
    ) -> str:
        """
        Ensure an application row exists.

        Existing progressed statuses are never reset.
        Database updates happen only when routing or
        eligibility-assistance state changes.
        """

        desired_method = (
            "MANUAL"
            if route
            == "MANUAL_PRIORITY"
            else "AGENT"
        )

        existing = (
            self._get_application(
                job_id
            )
        )

        if existing:

            application_id = (
                existing[
                    "id"
                ]
            )

            status = (
                existing.get(
                    "status"
                )
            )

            if status not in {
                "PENDING",
                "IN_PROGRESS",
            }:

                return (
                    application_id
                )

            update_payload = {}

            current_method = (
                existing.get(
                    "application_method"
                )
            )

            if (
                current_method
                != desired_method
            ):

                update_payload[
                    "application_method"
                ] = (
                    desired_method
                )

            assistance_reason = (
                existing.get(
                    "assistance_reason"
                )
                or ""
            )

            if (
                existing.get(
                    "needs_assistance"
                )
                and assistance_reason.startswith(
                    "ELIGIBILITY:"
                )
            ):

                update_payload[
                    "needs_assistance"
                ] = False

                update_payload[
                    "assistance_reason"
                ] = None

            if update_payload:

                update_payload[
                    "last_updated_at"
                ] = (
                    utc_now()
                )

                (
                    self.client
                    .table(
                        "applications"
                    )
                    .update(
                        update_payload
                    )
                    .eq(
                        "id",
                        application_id,
                    )
                    .eq(
                        "owner_id",
                        self.owner_id,
                    )
                    .execute()
                )

            return (
                application_id
            )

        payload = {
            "owner_id": (
                self.owner_id
            ),

            "job_id": (
                job_id
            ),

            "application_method": (
                desired_method
            ),

            "status": (
                "PENDING"
            ),

            "needs_assistance": False,
        }

        response = (
            self.client
            .table(
                "applications"
            )
            .insert(
                payload
            )
            .execute()
        )

        if not response.data:

            raise RuntimeError(
                "Failed to create "
                "application tracker row."
            )

        return (
            response.data[0][
                "id"
            ]
        )

    # ========================================================
    # BROWSER ROUTE GUARD
    # ========================================================

    def get_latest_evaluation_route(
        self,
        *,
        job_id: str,
    ):
        """
        Return the route from the newest completed evaluation
        for this job.

        Browser automation is only valid for AGENT_APPLY jobs.
        """

        evaluations = (
            self.client
            .table(
                "job_evaluations"
            )
            .select(
                "run_id,route"
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "job_id",
                job_id,
            )
            .execute()
        )

        rows = (
            evaluations.data
            or []
        )

        if not rows:

            return None

        run_ids = [
            row.get(
                "run_id"
            )
            for row in rows
            if row.get(
                "run_id"
            )
        ]

        if not run_ids:

            return None

        runs = (
            self.client
            .table(
                "agent_runs"
            )
            .select(
                "id,completed_at"
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .in_(
                "id",
                run_ids,
            )
            .execute()
        )

        completed_by_run = {
            row.get(
                "id"
            ): (
                row.get(
                    "completed_at"
                )
                or ""
            )
            for row in (
                runs.data
                or []
            )
        }

        ranked = sorted(
            rows,
            key=lambda row: (
                completed_by_run.get(
                    row.get(
                        "run_id"
                    ),
                    "",
                ),
                str(
                    row.get(
                        "run_id"
                    )
                    or ""
                ),
            ),
            reverse=True,
        )

        return (
            ranked[0].get(
                "route"
            )
        )

    def assert_browser_route_allowed(
        self,
        *,
        job_id: str,
    ) -> str:
        """
        Fail closed unless the newest completed matcher route
        is AGENT_APPLY.
        """

        route = (
            self.get_latest_evaluation_route(
                job_id=(
                    job_id
                ),
            )
        )

        if route != "AGENT_APPLY":

            raise RuntimeError(
                "Browser handoff persistence blocked: "
                "latest evaluation route must be "
                f"AGENT_APPLY, found {route!r}."
            )

        return route

    def get_browser_execution_context(
        self,
        *,
        job_id: str,
    ) -> dict:
        """
        Return the current job, latest completed evaluation,
        and application state used by Browser Orchestrator V1.
        """

        job_response = (
            self.client
            .table(
                "jobs"
            )
            .select(
                (
                    "id,"
                    "board_token,"
                    "greenhouse_job_id,"
                    "company,"
                    "title,"
                    "url,"
                    "is_active"
                )
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "id",
                job_id,
            )
            .limit(
                1
            )
            .execute()
        )

        if not job_response.data:

            raise RuntimeError(
                "Browser execution blocked: "
                "job row was not found."
            )

        job = (
            job_response.data[0]
        )

        evaluations = (
            self.client
            .table(
                "job_evaluations"
            )
            .select(
                (
                    "run_id,"
                    "route,"
                    "selected_resume,"
                    "selected_resume_file,"
                    "score,"
                    "selection_score,"
                    "confidence"
                )
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "job_id",
                job_id,
            )
            .execute()
        )

        evaluation_rows = (
            evaluations.data
            or []
        )

        latest_evaluation = None

        if evaluation_rows:

            run_ids = [
                row.get(
                    "run_id"
                )
                for row in (
                    evaluation_rows
                )
                if row.get(
                    "run_id"
                )
            ]

            completed_by_run = {}

            if run_ids:

                runs = (
                    self.client
                    .table(
                        "agent_runs"
                    )
                    .select(
                        "id,completed_at"
                    )
                    .eq(
                        "owner_id",
                        self.owner_id,
                    )
                    .in_(
                        "id",
                        run_ids,
                    )
                    .execute()
                )

                completed_by_run = {
                    row.get(
                        "id"
                    ): (
                        row.get(
                            "completed_at"
                        )
                        or ""
                    )
                    for row in (
                        runs.data
                        or []
                    )
                }

            ranked = sorted(
                evaluation_rows,
                key=lambda row: (
                    completed_by_run.get(
                        row.get(
                            "run_id"
                        ),
                        "",
                    ),
                    str(
                        row.get(
                            "run_id"
                        )
                        or ""
                    ),
                ),
                reverse=True,
            )

            latest_evaluation = (
                ranked[0]
            )

        application = (
            self._get_application(
                job_id
            )
        )

        return {
            "job": job,
            "evaluation": (
                latest_evaluation
            ),
            "application": (
                application
            ),
        }

    def assert_browser_execution_allowed(
        self,
        *,
        job_id: str,
    ) -> dict:
        """
        Fail closed before Browser Orchestrator V1 opens a page.

        Required state:
            - active tracked job
            - latest completed route is AGENT_APPLY
            - application row already exists
            - application method is AGENT
            - status is PENDING or IN_PROGRESS
            - no non-browser assistance is active
            - selected resume file is present in evaluation metadata
        """

        context = (
            self.get_browser_execution_context(
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

        application = (
            context[
                "application"
            ]
        )

        if job.get(
            "is_active",
            True,
        ) is False:

            raise RuntimeError(
                "Browser execution blocked: "
                "job is no longer active."
            )

        route = (
            evaluation.get(
                "route"
            )
            if evaluation
            else None
        )

        if route != "AGENT_APPLY":

            raise RuntimeError(
                "Browser execution blocked: "
                "latest evaluation route must be "
                f"AGENT_APPLY, found {route!r}."
            )

        if not application:

            raise RuntimeError(
                "Browser execution blocked: "
                "application tracker row is missing."
            )

        if (
            application.get(
                "application_method"
            )
            != "AGENT"
        ):

            raise RuntimeError(
                "Browser execution blocked: "
                "application_method must be AGENT, "
                f"found {application.get('application_method')!r}."
            )

        if application.get(
            "status"
        ) not in {
            "PENDING",
            "IN_PROGRESS",
        }:

            raise RuntimeError(
                "Browser execution blocked: "
                "application status must be PENDING "
                "or IN_PROGRESS."
            )

        assistance_reason = (
            application.get(
                "assistance_reason"
            )
            or ""
        )

        if (
            application.get(
                "needs_assistance"
            )
            and not assistance_reason.startswith(
                "BROWSER:"
            )
        ):

            raise RuntimeError(
                "Browser execution blocked: "
                "non-browser assistance is already active."
            )

        selected_resume_file = (
            evaluation.get(
                "selected_resume_file"
            )
            if evaluation
            else None
        )

        if not selected_resume_file:

            raise RuntimeError(
                "Browser execution blocked: "
                "selected_resume_file is missing "
                "from the latest evaluation."
            )

        return context

    # ========================================================
    # BROWSER QUEUE RUNNER
    # ========================================================

    def list_browser_queue_candidates(
        self,
        *,
        limit: int = 3,
        include_in_progress: bool = False,
        board_token: str | None = None,
        order: str = "oldest",
    ) -> list[dict]:
        """
        Return safe Browser Queue Runner V1 candidates.

        Candidate rules:
            - application_method == AGENT
            - status == PENDING by default
            - optionally include IN_PROGRESS
            - needs_assistance == False
            - active tracked job
            - optional board_token filter
            - latest *completed* evaluation route == AGENT_APPLY
            - latest evaluation has selected_resume_file

        Score affects ordering only when order='fit'; it never
        removes an otherwise eligible queue candidate.
        """

        if not isinstance(
            limit,
            int,
        ) or not (
            1
            <= limit
            <= 50
        ):

            raise ValueError(
                "Browser queue limit must be an integer from 1 to 50."
            )

        if order not in {
            "oldest",
            "newest",
            "fit",
        }:

            raise ValueError(
                "Browser queue order must be one of: "
                "oldest, newest, fit."
            )

        allowed_statuses = {
            "PENDING",
        }

        if include_in_progress:
            allowed_statuses.add(
                "IN_PROGRESS"
            )

        applications_response = (
            self.client
            .table(
                "applications"
            )
            .select(
                (
                    "id,"
                    "job_id,"
                    "application_method,"
                    "status,"
                    "needs_assistance,"
                    "assistance_reason,"
                    "created_at,"
                    "last_updated_at"
                )
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "application_method",
                "AGENT",
            )
            .execute()
        )

        applications = [
            row
            for row in (
                applications_response.data
                or []
            )
            if (
                row.get(
                    "status"
                )
                in allowed_statuses
                and not bool(
                    row.get(
                        "needs_assistance"
                    )
                )
            )
        ]

        if not applications:

            return []

        application_by_job = {
            row.get(
                "job_id"
            ): row
            for row in (
                applications
            )
            if row.get(
                "job_id"
            )
        }

        job_ids = list(
            application_by_job
        )

        jobs_response = (
            self.client
            .table(
                "jobs"
            )
            .select(
                (
                    "id,"
                    "board_token,"
                    "greenhouse_job_id,"
                    "company,"
                    "title,"
                    "url,"
                    "is_active"
                )
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .in_(
                "id",
                job_ids,
            )
            .execute()
        )

        jobs = [
            row
            for row in (
                jobs_response.data
                or []
            )
            if (
                row.get(
                    "is_active",
                    True,
                )
                is not False
                and (
                    board_token
                    is None
                    or row.get(
                        "board_token"
                    )
                    == board_token
                )
            )
        ]

        if not jobs:

            return []

        job_by_id = {
            row.get(
                "id"
            ): row
            for row in (
                jobs
            )
            if row.get(
                "id"
            )
        }

        live_job_ids = list(
            job_by_id
        )

        evaluations_response = (
            self.client
            .table(
                "job_evaluations"
            )
            .select(
                (
                    "job_id,"
                    "run_id,"
                    "route,"
                    "selected_resume,"
                    "selected_resume_file,"
                    "score,"
                    "selection_score,"
                    "confidence"
                )
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .in_(
                "job_id",
                live_job_ids,
            )
            .execute()
        )

        evaluations = (
            evaluations_response.data
            or []
        )

        if not evaluations:

            return []

        run_ids = list(
            {
                row.get(
                    "run_id"
                )
                for row in (
                    evaluations
                )
                if row.get(
                    "run_id"
                )
            }
        )

        if not run_ids:

            return []

        runs_response = (
            self.client
            .table(
                "agent_runs"
            )
            .select(
                "id,completed_at"
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .in_(
                "id",
                run_ids,
            )
            .execute()
        )

        completed_by_run = {
            row.get(
                "id"
            ): row.get(
                "completed_at"
            )
            for row in (
                runs_response.data
                or []
            )
            if (
                row.get(
                    "id"
                )
                and row.get(
                    "completed_at"
                )
            )
        }

        latest_evaluation_by_job = {}

        for evaluation in evaluations:

            run_id = (
                evaluation.get(
                    "run_id"
                )
            )

            completed_at = (
                completed_by_run.get(
                    run_id
                )
            )

            if not completed_at:
                continue

            job_id = (
                evaluation.get(
                    "job_id"
                )
            )

            if not job_id:
                continue

            current = (
                latest_evaluation_by_job.get(
                    job_id
                )
            )

            current_completed_at = (
                current.get(
                    "_completed_at"
                )
                if current
                else None
            )

            if (
                current is None
                or completed_at
                > current_completed_at
            ):

                row = dict(
                    evaluation
                )

                row[
                    "_completed_at"
                ] = completed_at

                latest_evaluation_by_job[
                    job_id
                ] = row

        candidates = []

        for job_id, job in (
            job_by_id.items()
        ):

            application = (
                application_by_job.get(
                    job_id
                )
            )

            evaluation = (
                latest_evaluation_by_job.get(
                    job_id
                )
            )

            if (
                not application
                or not evaluation
            ):
                continue

            if (
                evaluation.get(
                    "route"
                )
                != "AGENT_APPLY"
            ):
                continue

            selected_resume_file = (
                evaluation.get(
                    "selected_resume_file"
                )
            )

            if not selected_resume_file:
                continue

            candidates.append(
                {
                    "job_id": (
                        job_id
                    ),
                    "application_id": (
                        application.get(
                            "id"
                        )
                    ),
                    "application_status": (
                        application.get(
                            "status"
                        )
                    ),
                    "application_created_at": (
                        application.get(
                            "created_at"
                        )
                        or ""
                    ),
                    "board_token": (
                        job.get(
                            "board_token"
                        )
                    ),
                    "greenhouse_job_id": (
                        job.get(
                            "greenhouse_job_id"
                        )
                    ),
                    "company": (
                        job.get(
                            "company"
                        )
                    ),
                    "title": (
                        job.get(
                            "title"
                        )
                    ),
                    "url": (
                        job.get(
                            "url"
                        )
                    ),
                    "route": (
                        evaluation.get(
                            "route"
                        )
                    ),
                    "score": (
                        evaluation.get(
                            "score"
                        )
                    ),
                    "selection_score": (
                        evaluation.get(
                            "selection_score"
                        )
                    ),
                    "confidence": (
                        evaluation.get(
                            "confidence"
                        )
                    ),
                    "selected_resume": (
                        evaluation.get(
                            "selected_resume"
                        )
                    ),
                    "selected_resume_file": (
                        selected_resume_file
                    ),
                    "evaluation_completed_at": (
                        evaluation.get(
                            "_completed_at"
                        )
                    ),
                }
            )

        if order == "fit":

            candidates.sort(
                key=lambda row: (
                    -float(
                        row.get(
                            "score"
                        )
                        or 0
                    ),
                    row.get(
                        "application_created_at"
                    )
                    or "9999",
                    str(
                        row.get(
                            "job_id"
                        )
                        or ""
                    ),
                )
            )

        elif order == "newest":

            candidates.sort(
                key=lambda row: (
                    row.get(
                        "application_created_at"
                    )
                    or "",
                    str(
                        row.get(
                            "job_id"
                        )
                        or ""
                    ),
                ),
                reverse=True,
            )

        else:

            candidates.sort(
                key=lambda row: (
                    row.get(
                        "application_created_at"
                    )
                    or "9999",
                    str(
                        row.get(
                            "job_id"
                        )
                        or ""
                    ),
                )
            )

        return candidates[
            :limit
        ]

    def mark_browser_ready_no_submit(
        self,
        *,
        job_id: str,
    ) -> str:
        """
        Mark a PENDING application IN_PROGRESS after a persisted
        READY_NO_SUBMIT queue outcome.

        This prevents Browser Queue Runner V1 from repeatedly
        reprocessing the same fully deterministic application.
        It never marks the application APPLIED.
        """

        application = (
            self._get_application(
                job_id
            )
        )

        if not application:

            raise RuntimeError(
                "Browser queue state update blocked: "
                "application tracker row is missing."
            )

        application_id = (
            application[
                "id"
            ]
        )

        status = (
            application.get(
                "status"
            )
        )

        if status == "PENDING":

            (
                self.client
                .table(
                    "applications"
                )
                .update(
                    {
                        "status": (
                            "IN_PROGRESS"
                        ),
                        "last_updated_at": (
                            utc_now()
                        ),
                    }
                )
                .eq(
                    "owner_id",
                    self.owner_id,
                )
                .eq(
                    "id",
                    application_id,
                )
                .execute()
            )

        elif status != "IN_PROGRESS":

            raise RuntimeError(
                "Browser queue state update blocked: "
                "application is no longer PENDING "
                "or IN_PROGRESS."
            )

        return application_id

    # ========================================================
    # BROWSER QUEUE RUN HISTORY
    # ========================================================

    def sync_browser_queue_run_history(
        self,
        report,
    ) -> str:
        """
        Persist one sanitized Browser Queue Runner summary.

        Unique on owner_id + run_key so retries update the same
        operational history row rather than duplicating it.
        """

        payload = (
            sanitize_browser_queue_history_report(
                report
            )
        )

        payload[
            "owner_id"
        ] = self.owner_id

        response = (
            self.client
            .table(
                "browser_queue_runs"
            )
            .upsert(
                payload,
                on_conflict=(
                    "owner_id,run_key"
                ),
            )
            .execute()
        )

        if response.data:

            return str(
                response.data[
                    0
                ].get(
                    "id"
                )
                or payload[
                    "run_key"
                ]
            )

        lookup = (
            self.client
            .table(
                "browser_queue_runs"
            )
            .select(
                "id"
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "run_key",
                payload[
                    "run_key"
                ],
            )
            .limit(
                1
            )
            .execute()
        )

        if not lookup.data:

            raise RuntimeError(
                "Failed to persist Browser Queue "
                "Runner history."
            )

        return str(
            lookup.data[
                0
            ][
                "id"
            ]
        )

    # ========================================================
    # BROWSER ASSISTANCE HANDOFF
    # ========================================================

    def find_job_id(
        self,
        *,
        board_token: str,
        greenhouse_job_id,
    ):
        """
        Resolve the internal jobs.id for a known Greenhouse job.
        """

        response = (
            self.client
            .table(
                "jobs"
            )
            .select(
                "id"
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "board_token",
                board_token,
            )
            .eq(
                "greenhouse_job_id",
                str(
                    greenhouse_job_id
                ),
            )
            .limit(
                1
            )
            .execute()
        )

        if response.data:

            return (
                response.data[0][
                    "id"
                ]
            )

        return None

    def sync_browser_assistance_handoff(
        self,
        *,
        job_id: str,
        handoff: dict,
    ) -> str:
        """
        Persist or clear Browser Agent assistance state.

        NEEDS_ASSISTANCE:
            - application stays PENDING/IN_PROGRESS
            - needs_assistance=True
            - application reason uses a compact BROWSER: tag
            - one unresolved BROWSER assistance request is upserted
            - structured handoff is persisted in redacted form

        AGENT_CONTINUE:
            - only BROWSER assistance is cleared
            - eligibility or unrelated assistance is preserved
            - unresolved BROWSER requests are resolved

        Progressed application statuses are never reset.
        """

        self.assert_browser_route_allowed(
            job_id=(
                job_id
            ),
        )

        safe_handoff = (
            sanitize_browser_handoff(
                handoff
            )
        )

        route = (
            safe_handoff[
                "route"
            ]
        )

        existing = (
            self._get_application(
                job_id
            )
        )

        if (
            route
            == BROWSER_ROUTE_AGENT_CONTINUE
        ):

            if not existing:

                return (
                    self.ensure_application(
                        job_id=(
                            job_id
                        ),

                        route=(
                            "AGENT_APPLY"
                        ),
                    )
                )

            application_id = (
                existing[
                    "id"
                ]
            )

            status = (
                existing.get(
                    "status"
                )
            )

            if status not in {
                "PENDING",
                "IN_PROGRESS",
            }:

                return (
                    application_id
                )

            current_reason = (
                existing.get(
                    "assistance_reason"
                )
                or ""
            )

            if (
                existing.get(
                    "needs_assistance"
                )
                and current_reason.startswith(
                    "BROWSER:"
                )
            ):

                (
                    self.client
                    .table(
                        "applications"
                    )
                    .update(
                        {
                            "needs_assistance": False,
                            "assistance_reason": None,
                            "last_updated_at": (
                                utc_now()
                            ),
                        }
                    )
                    .eq(
                        "id",
                        application_id,
                    )
                    .eq(
                        "owner_id",
                        self.owner_id,
                    )
                    .execute()
                )

            self._resolve_browser_assistance_requests(
                application_id=(
                    application_id
                ),
            )

            return (
                application_id
            )

        reason = (
            build_browser_assistance_reason(
                safe_handoff
            )
        )

        question = (
            build_browser_assistance_question(
                safe_handoff
            )
        )

        if existing:

            application_id = (
                existing[
                    "id"
                ]
            )

            status = (
                existing.get(
                    "status"
                )
            )

            if status not in {
                "PENDING",
                "IN_PROGRESS",
            }:

                return (
                    application_id
                )

            current_assistance = (
                bool(
                    existing.get(
                        "needs_assistance"
                    )
                )
            )

            current_reason = (
                existing.get(
                    "assistance_reason"
                )
                or ""
            )

            update_payload = {}

            if not current_assistance:

                update_payload[
                    "needs_assistance"
                ] = True

            # Never clobber eligibility or unrelated
            # assistance with a browser-stage reason.
            if (
                not current_reason
                or current_reason.startswith(
                    "BROWSER:"
                )
            ):

                if (
                    current_reason
                    != reason
                ):

                    update_payload[
                        "assistance_reason"
                    ] = (
                        reason
                    )

            if update_payload:

                update_payload[
                    "last_updated_at"
                ] = (
                    utc_now()
                )

                (
                    self.client
                    .table(
                        "applications"
                    )
                    .update(
                        update_payload
                    )
                    .eq(
                        "id",
                        application_id,
                    )
                    .eq(
                        "owner_id",
                        self.owner_id,
                    )
                    .execute()
                )

            self._ensure_browser_assistance_request(
                application_id=(
                    application_id
                ),

                reason=(
                    reason
                ),

                question=(
                    question
                ),

                handoff=(
                    safe_handoff
                ),
            )

            return (
                application_id
            )

        payload = {
            "owner_id": (
                self.owner_id
            ),

            "job_id": (
                job_id
            ),

            "application_method": (
                "AGENT"
            ),

            "status": (
                "PENDING"
            ),

            "needs_assistance": True,

            "assistance_reason": (
                reason
            ),
        }

        response = (
            self.client
            .table(
                "applications"
            )
            .insert(
                payload
            )
            .execute()
        )

        if not response.data:

            raise RuntimeError(
                "Failed to create browser "
                "assistance application row."
            )

        application_id = (
            response.data[0][
                "id"
            ]
        )

        self._ensure_browser_assistance_request(
            application_id=(
                application_id
            ),

            reason=(
                reason
            ),

            question=(
                question
            ),

            handoff=(
                safe_handoff
            ),
        )

        return (
            application_id
        )

    def _ensure_browser_assistance_request(
        self,
        *,
        application_id: str,
        reason: str,
        question: str,
        handoff: dict,
    ) -> None:
        """
        Keep exactly one unresolved BROWSER assistance request
        per application. Database unique index provides the final
        concurrency guard.
        """

        safe_handoff = (
            sanitize_browser_handoff(
                handoff
            )
        )

        existing = (
            self.client
            .table(
                "assistance_requests"
            )
            .select(
                (
                    "id,"
                    "reason,"
                    "question,"
                    "handoff,"
                    "handoff_version,"
                    "source,"
                    "resolved"
                )
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "application_id",
                application_id,
            )
            .eq(
                "source",
                "BROWSER",
            )
            .eq(
                "resolved",
                False,
            )
            .execute()
        )

        rows = (
            existing.data
            or []
        )

        if rows:

            primary = (
                rows[0]
            )

            update_payload = {}

            if (
                primary.get(
                    "reason"
                )
                != reason
            ):

                update_payload[
                    "reason"
                ] = (
                    reason
                )

            if (
                primary.get(
                    "question"
                )
                != question
            ):

                update_payload[
                    "question"
                ] = (
                    question
                )

            if (
                primary.get(
                    "handoff"
                )
                != safe_handoff
            ):

                update_payload[
                    "handoff"
                ] = (
                    safe_handoff
                )

            if (
                primary.get(
                    "handoff_version"
                )
                != BROWSER_HANDOFF_VERSION
            ):

                update_payload[
                    "handoff_version"
                ] = (
                    BROWSER_HANDOFF_VERSION
                )

            if update_payload:

                update_payload[
                    "updated_at"
                ] = (
                    utc_now()
                )

                (
                    self.client
                    .table(
                        "assistance_requests"
                    )
                    .update(
                        update_payload
                    )
                    .eq(
                        "id",
                        primary[
                            "id"
                        ],
                    )
                    .eq(
                        "owner_id",
                        self.owner_id,
                    )
                    .execute()
                )

            # Defensive cleanup for historical duplicates.
            for duplicate in (
                rows[1:]
            ):

                (
                    self.client
                    .table(
                        "assistance_requests"
                    )
                    .update(
                        {
                            "resolved": True,
                            "updated_at": (
                                utc_now()
                            ),
                        }
                    )
                    .eq(
                        "id",
                        duplicate[
                            "id"
                        ],
                    )
                    .eq(
                        "owner_id",
                        self.owner_id,
                    )
                    .execute()
                )

            return

        payload = {
            "owner_id": (
                self.owner_id
            ),

            "application_id": (
                application_id
            ),

            "question": (
                question
            ),

            "reason": (
                reason
            ),

            "resolved": False,

            "source": (
                "BROWSER"
            ),

            "handoff_version": (
                BROWSER_HANDOFF_VERSION
            ),

            "handoff": (
                safe_handoff
            ),

            "updated_at": (
                utc_now()
            ),
        }

        (
            self.client
            .table(
                "assistance_requests"
            )
            .insert(
                payload
            )
            .execute()
        )

    def _resolve_browser_assistance_requests(
        self,
        *,
        application_id: str,
    ) -> None:
        """
        Resolve only Browser Agent requests.
        Eligibility assistance remains untouched.
        """

        (
            self.client
            .table(
                "assistance_requests"
            )
            .update(
                {
                    "resolved": True,
                    "updated_at": (
                        utc_now()
                    ),
                }
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "application_id",
                application_id,
            )
            .eq(
                "source",
                "BROWSER",
            )
            .eq(
                "resolved",
                False,
            )
            .execute()
        )

    # ========================================================
    # NEEDS ASSISTANCE
    # ========================================================

    def ensure_assistance_application(
        self,
        *,
        job_id: str,
        reason: str,
    ) -> str:
        """
        Ensure a job requiring human review appears in
        the assistance queue.

        Existing progressed applications are preserved.
        Writes only occur when the assistance state or
        assistance reason actually changes.
        """

        tagged_reason = (
            f"ELIGIBILITY: {reason}"
        )

        existing = (
            self._get_application(
                job_id
            )
        )

        if existing:

            application_id = (
                existing[
                    "id"
                ]
            )

            status = (
                existing.get(
                    "status"
                )
            )

            if status not in {
                "PENDING",
                "IN_PROGRESS",
            }:

                return (
                    application_id
                )

            update_payload = {}

            current_assistance = (
                bool(
                    existing.get(
                        "needs_assistance"
                    )
                )
            )

            current_reason = (
                existing.get(
                    "assistance_reason"
                )
            )

            if not current_assistance:

                update_payload[
                    "needs_assistance"
                ] = True

            if (
                current_reason
                != tagged_reason
            ):

                update_payload[
                    "assistance_reason"
                ] = (
                    tagged_reason
                )

            if update_payload:

                update_payload[
                    "last_updated_at"
                ] = (
                    utc_now()
                )

                (
                    self.client
                    .table(
                        "applications"
                    )
                    .update(
                        update_payload
                    )
                    .eq(
                        "id",
                        application_id,
                    )
                    .eq(
                        "owner_id",
                        self.owner_id,
                    )
                    .execute()
                )

            self._ensure_assistance_request(
                application_id=(
                    application_id
                ),

                reason=(
                    tagged_reason
                ),
            )

            return (
                application_id
            )

        payload = {
            "owner_id": (
                self.owner_id
            ),

            "job_id": (
                job_id
            ),

            "application_method": (
                "AGENT"
            ),

            "status": (
                "PENDING"
            ),

            "needs_assistance": True,

            "assistance_reason": (
                tagged_reason
            ),
        }

        response = (
            self.client
            .table(
                "applications"
            )
            .insert(
                payload
            )
            .execute()
        )

        if not response.data:

            raise RuntimeError(
                "Failed to create assistance "
                "application tracker row."
            )

        application_id = (
            response.data[0][
                "id"
            ]
        )

        self._ensure_assistance_request(
            application_id=(
                application_id
            ),

            reason=(
                tagged_reason
            ),
        )

        return (
            application_id
        )

    # ========================================================
    # ASSISTANCE REQUESTS
    # ========================================================

    def _ensure_assistance_request(
        self,
        *,
        application_id: str,
        reason: str,
    ) -> None:
        """
        Prevent duplicate unresolved assistance requests.
        """

        existing = (
            self.client
            .table(
                "assistance_requests"
            )
            .select(
                "id,reason,resolved"
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "application_id",
                application_id,
            )
            .eq(
                "resolved",
                False,
            )
            .execute()
        )

        for request in (
            existing.data
            or []
        ):

            if (
                request.get(
                    "reason"
                )
                == reason
            ):

                return

        payload = {
            "owner_id": (
                self.owner_id
            ),

            "application_id": (
                application_id
            ),

            "question": (
                "Please review this job's "
                "eligibility requirements "
                "before application."
            ),

            "reason": (
                reason
            ),

            "resolved": False,
        }

        (
            self.client
            .table(
                "assistance_requests"
            )
            .insert(
                payload
            )
            .execute()
        )

