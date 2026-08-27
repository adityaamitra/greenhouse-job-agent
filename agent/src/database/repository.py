from datetime import datetime, timezone

from src.database.supabase_client import (
    get_owner_id,
    get_supabase_client,
)


def utc_now() -> str:
    """
    Return current UTC timestamp in ISO format.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


class JobRepository:
    """
    Database layer for the Greenhouse Job Agent.

    Responsibilities:
        - Agent run history
        - Job persistence
        - Match-score history
        - Application tracker creation
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
        """
        Start a new agent scan.
        """

        payload = {
            "owner_id": self.owner_id,
            "board_token": board_token,
        }

        response = (
            self.client
            .table("agent_runs")
            .insert(payload)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to create agent run."
            )

        return response.data[0]["id"]

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
        """
        Save final statistics for an agent scan.
        """

        payload = {
            "completed_at": utc_now(),

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
            .table("agent_runs")
            .update(payload)
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
        """
        Insert a new Greenhouse job or update an existing one.

        Job uniqueness:
            owner_id
            board_token
            greenhouse_job_id
        """

        now = utc_now()

        payload = {
            "owner_id": self.owner_id,

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
            .table("jobs")
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

            return response.data[0][
                "id"
            ]

        # Fallback lookup in case the API did not
        # return the inserted/upserted row.
        lookup = (
            self.client
            .table("jobs")
            .select("id")
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
            .limit(1)
            .execute()
        )

        if not lookup.data:

            raise RuntimeError(
                "Job was upserted but could "
                "not be retrieved."
            )

        return lookup.data[0]["id"]

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
        Store the resume-selection result for a job.
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
    # APPLICATION TRACKER
    # ========================================================

    def ensure_application(
        self,
        *,
        job_id: str,
        route: str,
    ) -> str:
        """
        Make sure an application tracker row exists.

        Existing application statuses are NEVER reset.

        Example:
            If a job is already INTERVIEW,
            another scan must not change it back to PENDING.
        """

        existing = (
            self.client
            .table("applications")
            .select(
                "id, status"
            )
            .eq(
                "owner_id",
                self.owner_id,
            )
            .eq(
                "job_id",
                job_id,
            )
            .limit(1)
            .execute()
        )

        if existing.data:

            return existing.data[0][
                "id"
            ]

        if route == "MANUAL_PRIORITY":

            application_method = (
                "MANUAL"
            )

        else:

            application_method = (
                "AGENT"
            )

        payload = {
            "owner_id": (
                self.owner_id
            ),

            "job_id": (
                job_id
            ),

            "application_method": (
                application_method
            ),

            "status": (
                "PENDING"
            ),

            "needs_assistance": (
                False
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
                "Failed to create "
                "application tracker row."
            )

        return response.data[0][
            "id"
        ]
