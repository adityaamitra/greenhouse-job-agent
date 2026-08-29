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
# REPOSITORY
# ============================================================

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

