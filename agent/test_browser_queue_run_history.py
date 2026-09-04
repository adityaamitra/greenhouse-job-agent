import json
from pathlib import Path
import tempfile
import sys
import types


stub = types.ModuleType(
    "src.database.supabase_client"
)
stub.get_owner_id = lambda: "owner-1"
stub.get_supabase_client = lambda: None
sys.modules[
    "src.database.supabase_client"
] = stub


from src.browser.queue_runner import (  # noqa: E402
    run_browser_queue,
)
from src.database.repository import (  # noqa: E402
    JobRepository,
    sanitize_browser_queue_history_report,
)
from src.profile.applicant_profile import (  # noqa: E402
    ApplicantProfile,
)


class FakeResponse:
    def __init__(
        self,
        data,
    ):
        self.data = data


class FakeQuery:
    def __init__(
        self,
        client,
        table_name,
    ):
        self.client = client
        self.table_name = table_name
        self.filters = []
        self.payload = None
        self.operation = "select"

    def select(
        self,
        _columns,
    ):
        self.operation = "select"
        return self

    def eq(
        self,
        key,
        value,
    ):
        self.filters.append(
            (
                key,
                value,
            )
        )
        return self

    def limit(
        self,
        _value,
    ):
        return self

    def upsert(
        self,
        payload,
        on_conflict=None,
    ):
        self.operation = "upsert"
        self.payload = dict(
            payload
        )
        self.on_conflict = on_conflict
        return self

    def _matches(
        self,
        row,
    ):
        return all(
            row.get(
                key
            )
            == value
            for key, value in (
                self.filters
            )
        )

    def execute(
        self,
    ):
        rows = self.client.tables.setdefault(
            self.table_name,
            [],
        )

        if self.operation == "upsert":
            existing = next(
                (
                    row
                    for row in rows
                    if (
                        row.get(
                            "owner_id"
                        )
                        == self.payload.get(
                            "owner_id"
                        )
                        and row.get(
                            "run_key"
                        )
                        == self.payload.get(
                            "run_key"
                        )
                    )
                ),
                None,
            )

            if existing is None:
                stored = dict(
                    self.payload
                )
                stored[
                    "id"
                ] = (
                    f"history-{len(rows) + 1}"
                )
                rows.append(
                    stored
                )
            else:
                existing.update(
                    self.payload
                )
                stored = existing

            self.client.last_upsert = dict(
                stored
            )

            return FakeResponse(
                [
                    dict(
                        stored
                    )
                ]
            )

        return FakeResponse(
            [
                dict(
                    row
                )
                for row in rows
                if self._matches(
                    row
                )
            ]
        )


class FakeClient:
    def __init__(
        self,
    ):
        self.tables = {
            "browser_queue_runs": [],
        }
        self.last_upsert = None

    def table(
        self,
        name,
    ):
        return FakeQuery(
            self,
            name,
        )


class QueueRepository:
    def __init__(
        self,
    ):
        self.history_reports = []

    def list_browser_queue_candidates(
        self,
        *,
        limit,
        include_in_progress,
        board_token,
        order,
    ):
        return [
            {
                "job_id": "job-1",
                "application_id": "app-1",
                "application_status": "PENDING",
                "board_token": "stripe",
                "greenhouse_job_id": "6042172",
                "company": "Stripe",
                "title": (
                    "Backend Engineer, Core Technology"
                ),
                "route": "AGENT_APPLY",
                "selected_resume_file": (
                    "backend_engineer.pdf"
                ),
            }
        ][
            :limit
        ]

    def sync_browser_queue_run_history(
        self,
        report,
    ):
        self.history_reports.append(
            json.loads(
                json.dumps(
                    report
                )
            )
        )
        return "history-1"

    def mark_browser_ready_no_submit(
        self,
        *,
        job_id,
    ):
        raise AssertionError(
            "Not expected for NEEDS_ASSISTANCE."
        )


def make_profile(
    directory: Path,
):
    payload = {
        "profile_version": 1,
        "identity": {
            "first_name": "PrivateFirst",
            "last_name": "PrivateLast",
            "preferred_first_name": "PrivateFirst",
        },
        "contact": {
            "email": "private@example.com",
            "phone": "+1-555-0100",
        },
        "links": {
            "linkedin_url": "https://example.com/in",
            "portfolio_url": "https://example.com",
            "github_url": "https://example.com/git",
        },
        "address": {
            "country": "United States",
            "city": "Boston",
            "state_or_province": "MA",
            "postal_code": "00000",
            "street_address": "1 Private Street",
            "location_freeform": "Boston, MA",
            "currently_in_us": True,
        },
        "education": {
            "school": "Example University",
            "degree": "Master of Science",
            "discipline": "Information Systems",
        },
        "work_authorization": {
            "authorized_to_work_us": True,
            "sponsorship_now": False,
            "sponsorship_future": True,
        },
    }

    path = directory / "profile.json"
    path.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )

    return ApplicantProfile.load(
        path
    )


def base_report():
    return {
        "queue_runner_version": 1,
        "run_id": "20260904T193249Z",
        "started_at": "2026-09-04T19:32:49+00:00",
        "completed_at": "2026-09-04T19:32:53+00:00",
        "total_seconds": 4.25,
        "persist": True,
        "limit": 1,
        "include_in_progress": False,
        "board_token_filter": "stripe",
        "order": "oldest",
        "summary": {},
        "results": [
            {
                "job_id": "private-db-id",
                "application_id": "private-app-id",
                "board_token": "stripe",
                "greenhouse_job_id": "6042172",
                "company": "Stripe",
                "title": "Backend Engineer",
                "selected_resume": "backend_engineer.pdf",
                "queue_status": "COMPLETED",
                "outcome": "NEEDS_ASSISTANCE",
                "challenge_detected": True,
                "ready_count": 8,
                "required_human_count": 6,
                "browser_modified": False,
                "application_status_after": "PENDING",
                "error_type": None,
                "error": (
                    "PrivateFirst private@example.com "
                    "/Users/private/path"
                ),
                "submit_clicked_by_agent": False,
                "application_submitted": False,
            }
        ],
        "submit_clicked_by_agent": False,
        "application_submitted": False,
    }


def main():
    tests = []

    sanitized = (
        sanitize_browser_queue_history_report(
            base_report()
        )
    )

    serialized = json.dumps(
        sanitized
    )

    tests.append(
        (
            "Sanitizer recomputes queue counts",
            (
                sanitized[
                    "selected_count"
                ]
                == 1
                and sanitized[
                    "completed_count"
                ]
                == 1
                and sanitized[
                    "needs_assistance_count"
                ]
                == 1
                and sanitized[
                    "challenge_count"
                ]
                == 1
            ),
        )
    )

    tests.append(
        (
            "Sanitized history excludes database ids and resume filename",
            (
                "private-db-id"
                not in serialized
                and "private-app-id"
                not in serialized
                and "backend_engineer.pdf"
                not in serialized
            ),
        )
    )

    tests.append(
        (
            "Sanitized history excludes arbitrary error messages and applicant PII",
            (
                "PrivateFirst"
                not in serialized
                and "private@example.com"
                not in serialized
                and "/Users/private/path"
                not in serialized
            ),
        )
    )

    tests.append(
        (
            "Submission fields are hard-coded false / zero",
            (
                sanitized[
                    "submitted_count"
                ]
                == 0
                and sanitized[
                    "submit_clicked_by_agent"
                ]
                is False
                and sanitized[
                    "application_submitted"
                ]
                is False
            ),
        )
    )

    bad = base_report()
    bad[
        "application_submitted"
    ] = True

    submission_blocked = False

    try:
        sanitize_browser_queue_history_report(
            bad
        )
    except RuntimeError:
        submission_blocked = True

    tests.append(
        (
            "History persistence fails closed if submission invariant is violated",
            submission_blocked,
        )
    )

    repository = object.__new__(
        JobRepository
    )
    repository.client = FakeClient()
    repository.owner_id = "owner-1"

    history_id = (
        repository
        .sync_browser_queue_run_history(
            base_report()
        )
    )

    tests.append(
        (
            "Repository upserts one owner-scoped history row",
            (
                history_id
                == "history-1"
                and len(
                    repository.client.tables[
                        "browser_queue_runs"
                    ]
                )
                == 1
                and repository.client.last_upsert[
                    "owner_id"
                ]
                == "owner-1"
            ),
        )
    )

    repository.sync_browser_queue_run_history(
        base_report()
    )

    tests.append(
        (
            "Same run_key updates instead of duplicating",
            len(
                repository.client.tables[
                    "browser_queue_runs"
                ]
            )
            == 1,
        )
    )

    with tempfile.TemporaryDirectory() as raw:
        directory = Path(
            raw
        )
        profile = make_profile(
            directory
        )
        queue_repository = (
            QueueRepository()
        )

        clocks = iter(
            [
                100.0,
                104.5,
            ]
        )

        def fake_orchestrate(
            **kwargs,
        ):
            return {
                "outcome": "NEEDS_ASSISTANCE",
                "challenge_detected": True,
                "ready_count": 8,
                "required_human_count": 6,
                "browser_modified": False,
                "persisted": True,
                "submit_clicked_by_agent": False,
                "application_submitted": False,
            }

        report = run_browser_queue(
            profile=profile,
            repository=queue_repository,
            limit=1,
            artifacts_dir=(
                directory
                / "queue"
            ),
            persist=True,
            delay_seconds=0,
            run_id="history-test",
            orchestrate_fn=(
                fake_orchestrate
            ),
            monotonic_fn=lambda: next(
                clocks
            ),
        )

        tests.append(
            (
                "Queue report records runtime and timestamps",
                (
                    report[
                        "total_seconds"
                    ]
                    == 4.5
                    and bool(
                        report[
                            "started_at"
                        ]
                    )
                    and bool(
                        report[
                            "completed_at"
                        ]
                    )
                ),
            )
        )

        tests.append(
            (
                "Persisted queue run writes one history summary",
                (
                    report[
                        "history_persisted"
                    ]
                    is True
                    and report[
                        "history_id"
                    ]
                    == "history-1"
                    and len(
                        queue_repository
                        .history_reports
                    )
                    == 1
                ),
            )
        )

        persisted = (
            queue_repository
            .history_reports[
                0
            ]
        )

        tests.append(
            (
                "Persisted report carries challenge / zero-submit operational state",
                (
                    persisted[
                        "summary"
                    ][
                        "challenge_count"
                    ]
                    == 1
                    and persisted[
                        "summary"
                    ][
                        "submitted"
                    ]
                    == 0
                    and persisted[
                        "application_submitted"
                    ]
                    is False
                ),
            )
        )

        dry_repository = (
            QueueRepository()
        )

        dry_clocks = iter(
            [
                200.0,
                201.0,
            ]
        )

        dry_report = run_browser_queue(
            profile=profile,
            repository=dry_repository,
            limit=1,
            artifacts_dir=(
                directory
                / "queue-dry"
            ),
            persist=False,
            delay_seconds=0,
            run_id="history-dry",
            orchestrate_fn=(
                fake_orchestrate
            ),
            monotonic_fn=lambda: next(
                dry_clocks
            ),
        )

        tests.append(
            (
                "No-persist mode writes no Supabase queue history",
                (
                    dry_report[
                        "history_persisted"
                    ]
                    is False
                    and not (
                        dry_repository
                        .history_reports
                    )
                ),
            )
        )

    migration = (
        Path(__file__)
        .resolve()
        .parent
        / "migrations"
        / "20260904_browser_queue_run_history_v1.sql"
    ).read_text(
        encoding="utf-8"
    )

    tests.append(
        (
            "Migration enables RLS and owner-only policies",
            (
                "enable row level security"
                in migration.lower()
                and "auth.uid() = owner_id"
                in migration
            ),
        )
    )

    tests.append(
        (
            "Database constraint hard-blocks persisted submission",
            (
                "browser_queue_runs_no_submission_check"
                in migration
                and "submitted_count = 0"
                in migration
                and "application_submitted = false"
                in migration
            ),
        )
    )

    print()
    print("=" * 104)
    print(
        "BROWSER QUEUE RUN HISTORY V1 TEST"
    )
    print("=" * 104)
    print()

    passed = 0

    for index, (
        name,
        ok,
    ) in enumerate(
        tests,
        start=1,
    ):
        print(
            f"{index:02}. "
            f"{'✅ PASS' if ok else '❌ FAIL'} — "
            f"{name}"
        )
        if ok:
            passed += 1

    failed = (
        len(
            tests
        )
        - passed
    )

    print()
    print("=" * 104)
    print(
        f"Passed: {passed}/{len(tests)}"
    )
    print(
        f"Failed: {failed}/{len(tests)}"
    )
    print()

    if failed:
        raise SystemExit(
            1
        )

    print(
        "✅ BROWSER QUEUE RUN HISTORY V1 TEST PASSED"
    )
    print("=" * 104)


if __name__ == "__main__":
    main()
