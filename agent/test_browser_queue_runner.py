import json
from pathlib import Path
import tempfile
import sys
import types


# Stub private Supabase helper before importing repository.py.
stub = types.ModuleType(
    "src.database.supabase_client"
)
stub.get_owner_id = lambda: "owner-1"
stub.get_supabase_client = lambda: None
sys.modules[
    "src.database.supabase_client"
] = stub


from src.browser.queue_runner import (  # noqa: E402
    preview_browser_queue,
    run_browser_queue,
)
from src.database.repository import (  # noqa: E402
    JobRepository,
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
        self.operation = "select"
        self.payload = None
        self.filters = []
        self.limit_value = None

    def select(
        self,
        _columns,
    ):
        return self

    def update(
        self,
        payload,
    ):
        self.operation = "update"
        self.payload = dict(
            payload
        )
        return self

    def eq(
        self,
        key,
        value,
    ):
        self.filters.append(
            (
                "EQ",
                key,
                value,
            )
        )
        return self

    def in_(
        self,
        key,
        values,
    ):
        self.filters.append(
            (
                "IN",
                key,
                set(
                    values
                ),
            )
        )
        return self

    def limit(
        self,
        value,
    ):
        self.limit_value = value
        return self

    def _matches(
        self,
        row,
    ):
        for kind, key, value in (
            self.filters
        ):

            if (
                kind
                == "EQ"
                and row.get(
                    key
                )
                != value
            ):
                return False

            if (
                kind
                == "IN"
                and row.get(
                    key
                )
                not in value
            ):
                return False

        return True

    def execute(
        self,
    ):
        rows = (
            self.client.tables[
                self.table_name
            ]
        )

        if self.operation == "update":

            updated = []

            for row in rows:

                if not self._matches(
                    row
                ):
                    continue

                row.update(
                    self.payload
                )

                updated.append(
                    dict(
                        row
                    )
                )

            return FakeResponse(
                updated
            )

        result = [
            dict(
                row
            )
            for row in rows
            if self._matches(
                row
            )
        ]

        if (
            self.limit_value
            is not None
        ):
            result = result[
                :self.limit_value
            ]

        return FakeResponse(
            result
        )


class FakeClient:
    def __init__(
        self,
    ):
        self.tables = {
            "applications": [],
            "jobs": [],
            "job_evaluations": [],
            "agent_runs": [],
            "assistance_requests": [],
        }

    def table(
        self,
        name,
    ):
        return FakeQuery(
            self,
            name,
        )


def make_repository():
    repository = object.__new__(
        JobRepository
    )
    repository.client = (
        FakeClient()
    )
    repository.owner_id = (
        "owner-1"
    )
    return repository


def add_candidate(
    repository,
    *,
    suffix,
    route="AGENT_APPLY",
    method="AGENT",
    status="PENDING",
    needs_assistance=False,
    active=True,
    board_token="example",
    created_at="2026-09-04T12:00:00+00:00",
    completed_at="2026-09-04T12:00:00+00:00",
    score=70,
    selected_resume_file="Software_Engineer.pdf",
):
    job_id = (
        f"job-{suffix}"
    )
    app_id = (
        f"app-{suffix}"
    )
    run_id = (
        f"run-{suffix}"
    )

    repository.client.tables[
        "applications"
    ].append(
        {
            "id": app_id,
            "owner_id": "owner-1",
            "job_id": job_id,
            "application_method": method,
            "status": status,
            "needs_assistance": (
                needs_assistance
            ),
            "assistance_reason": (
                "BROWSER: TEST"
                if needs_assistance
                else None
            ),
            "created_at": (
                created_at
            ),
            "last_updated_at": (
                created_at
            ),
        }
    )

    repository.client.tables[
        "jobs"
    ].append(
        {
            "id": job_id,
            "owner_id": "owner-1",
            "board_token": (
                board_token
            ),
            "greenhouse_job_id": (
                f"gh-{suffix}"
            ),
            "company": (
                f"Company {suffix}"
            ),
            "title": (
                f"Software Engineer {suffix}"
            ),
            "url": (
                "https://job-boards."
                "greenhouse.io/example/"
                f"jobs/gh-{suffix}"
            ),
            "is_active": active,
        }
    )

    repository.client.tables[
        "job_evaluations"
    ].append(
        {
            "owner_id": "owner-1",
            "job_id": job_id,
            "run_id": run_id,
            "route": route,
            "selected_resume": (
                "software_engineer"
            ),
            "selected_resume_file": (
                selected_resume_file
            ),
            "score": score,
            "selection_score": 80,
            "confidence": 90,
        }
    )

    repository.client.tables[
        "agent_runs"
    ].append(
        {
            "id": run_id,
            "owner_id": "owner-1",
            "completed_at": (
                completed_at
            ),
        }
    )

    return job_id


def make_profile(
    directory: Path,
):
    payload = {
        "profile_version": 1,
        "identity": {
            "first_name": (
                "PrivateFirst"
            ),
            "last_name": (
                "PrivateLast"
            ),
            "preferred_first_name": (
                "PrivateFirst"
            ),
        },
        "contact": {
            "email": (
                "private@example.com"
            ),
            "phone": (
                "+1-555-0100"
            ),
        },
        "links": {
            "linkedin_url": (
                "https://example.com/in"
            ),
            "portfolio_url": (
                "https://example.com"
            ),
            "github_url": (
                "https://example.com/git"
            ),
        },
        "address": {
            "country": (
                "United States"
            ),
            "city": "Boston",
            "state_or_province": "MA",
            "postal_code": "00000",
            "street_address": (
                "1 Private Street"
            ),
            "location_freeform": (
                "Boston, MA"
            ),
            "currently_in_us": True,
        },
        "education": {
            "school": (
                "Example University"
            ),
            "degree": (
                "Master of Science"
            ),
            "discipline": (
                "Information Systems"
            ),
        },
        "work_authorization": {
            "authorized_to_work_us": True,
            "sponsorship_now": False,
            "sponsorship_future": True,
        },
    }

    path = (
        directory
        / "profile.json"
    )

    path.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )

    return ApplicantProfile.load(
        path
    )


def main():
    tests = []

    repository = (
        make_repository()
    )

    add_candidate(
        repository,
        suffix="good-old",
        created_at=(
            "2026-09-01T12:00:00+00:00"
        ),
        score=60,
    )

    add_candidate(
        repository,
        suffix="good-new",
        created_at=(
            "2026-09-03T12:00:00+00:00"
        ),
        score=95,
    )

    add_candidate(
        repository,
        suffix="manual-route",
        route="MANUAL_PRIORITY",
    )

    add_candidate(
        repository,
        suffix="manual-method",
        method="MANUAL",
    )

    add_candidate(
        repository,
        suffix="assistance",
        needs_assistance=True,
    )

    add_candidate(
        repository,
        suffix="inactive",
        active=False,
    )

    add_candidate(
        repository,
        suffix="progress",
        status="IN_PROGRESS",
    )

    add_candidate(
        repository,
        suffix="other-board",
        board_token="other",
    )

    add_candidate(
        repository,
        suffix="no-resume",
        selected_resume_file=None,
    )

    queue = (
        repository
        .list_browser_queue_candidates(
            limit=20,
        )
    )

    queue_ids = {
        row[
            "job_id"
        ]
        for row in queue
    }

    tests.append(
        (
            "Default queue contains safe pending AGENT_APPLY jobs",
            (
                "job-good-old"
                in queue_ids
                and "job-good-new"
                in queue_ids
            ),
        )
    )

    tests.append(
        (
            "MANUAL_PRIORITY latest route is excluded",
            "job-manual-route"
            not in queue_ids,
        )
    )

    tests.append(
        (
            "MANUAL application method is excluded",
            "job-manual-method"
            not in queue_ids,
        )
    )

    tests.append(
        (
            "Needs Assistance row is excluded",
            "job-assistance"
            not in queue_ids,
        )
    )

    tests.append(
        (
            "Inactive job is excluded",
            "job-inactive"
            not in queue_ids,
        )
    )

    tests.append(
        (
            "IN_PROGRESS is excluded by default",
            "job-progress"
            not in queue_ids,
        )
    )

    tests.append(
        (
            "Missing selected resume metadata is excluded",
            "job-no-resume"
            not in queue_ids,
        )
    )

    with_progress = (
        repository
        .list_browser_queue_candidates(
            limit=20,
            include_in_progress=True,
        )
    )

    tests.append(
        (
            "IN_PROGRESS can be explicitly included",
            any(
                row[
                    "job_id"
                ]
                == "job-progress"
                for row in with_progress
            ),
        )
    )

    only_example = (
        repository
        .list_browser_queue_candidates(
            limit=20,
            board_token="example",
        )
    )

    tests.append(
        (
            "Board-token filter is respected",
            all(
                row[
                    "board_token"
                ]
                == "example"
                for row in only_example
            ),
        )
    )

    oldest = (
        repository
        .list_browser_queue_candidates(
            limit=20,
            order="oldest",
        )
    )

    tests.append(
        (
            "Oldest ordering uses application creation time",
            (
                oldest[
                    0
                ][
                    "job_id"
                ]
                == "job-good-old"
            ),
        )
    )

    fit = (
        repository
        .list_browser_queue_candidates(
            limit=20,
            order="fit",
        )
    )

    tests.append(
        (
            "Fit ordering changes priority but does not filter candidates",
            (
                fit[
                    0
                ][
                    "job_id"
                ]
                == "job-good-new"
                and {
                    row[
                        "job_id"
                    ]
                    for row in fit
                }
                == {
                    row[
                        "job_id"
                    ]
                    for row in oldest
                }
            ),
        )
    )

    tests.append(
        (
            "Limit bounds queue size",
            len(
                repository
                .list_browser_queue_candidates(
                    limit=2,
                )
            )
            == 2,
        )
    )

    # Queue execution behavior.
    execution_repo = (
        make_repository()
    )

    for suffix in [
        "one",
        "two",
        "three",
    ]:
        add_candidate(
            execution_repo,
            suffix=suffix,
            created_at=(
                f"2026-09-0"
                f"{1 + len(execution_repo.client.tables['jobs'])}"
                "T12:00:00+00:00"
            ),
        )

    with tempfile.TemporaryDirectory() as raw:
        directory = Path(
            raw
        )

        profile = make_profile(
            directory
        )

        calls = []
        marked = []

        original_mark = (
            execution_repo
            .mark_browser_ready_no_submit
        )

        def tracked_mark(
            *,
            job_id,
        ):
            marked.append(
                job_id
            )
            return original_mark(
                job_id=job_id
            )

        execution_repo.mark_browser_ready_no_submit = (
            tracked_mark
        )

        def fake_orchestrate(
            *,
            board_token,
            greenhouse_job_id,
            profile,
            resume_dir,
            artifacts_dir,
            headless,
            persist,
            repository,
        ):
            calls.append(
                {
                    "board_token": (
                        board_token
                    ),
                    "greenhouse_job_id": (
                        greenhouse_job_id
                    ),
                    "persist": (
                        persist
                    ),
                }
            )

            if (
                greenhouse_job_id
                == "gh-two"
            ):
                raise RuntimeError(
                    "Synthetic browser block."
                )

            outcome = (
                "READY_NO_SUBMIT"
                if greenhouse_job_id
                == "gh-one"
                else "NEEDS_ASSISTANCE"
            )

            return {
                "outcome": outcome,
                "challenge_detected": (
                    outcome
                    == "NEEDS_ASSISTANCE"
                ),
                "ready_count": 4,
                "required_human_count": (
                    2
                    if outcome
                    == "NEEDS_ASSISTANCE"
                    else 0
                ),
                "browser_modified": (
                    outcome
                    == "READY_NO_SUBMIT"
                ),
                "persisted": persist,
                "submit_clicked_by_agent": False,
                "application_submitted": False,
            }

        sleep_calls = []

        report = (
            run_browser_queue(
                profile=profile,
                repository=execution_repo,
                limit=3,
                resume_dir=(
                    directory
                    / "resumes"
                ),
                artifacts_dir=(
                    directory
                    / "queue"
                ),
                persist=True,
                delay_seconds=0.25,
                run_id="test-run",
                orchestrate_fn=(
                    fake_orchestrate
                ),
                sleep_fn=lambda seconds: (
                    sleep_calls.append(
                        seconds
                    )
                ),
            )
        )

        tests.append(
            (
                "Queue executes candidates sequentially with bounded delay",
                (
                    len(
                        calls
                    )
                    == 3
                    and sleep_calls
                    == [
                        0.25,
                        0.25,
                    ]
                ),
            )
        )

        tests.append(
            (
                "Per-job RuntimeError is isolated and later jobs continue",
                (
                    report[
                        "results"
                    ][
                        1
                    ][
                        "queue_status"
                    ]
                    == "BLOCKED"
                    and len(
                        report[
                            "results"
                        ]
                    )
                    == 3
                ),
            )
        )

        tests.append(
            (
                "Persistence flag is propagated to every orchestrator call",
                all(
                    call[
                        "persist"
                    ]
                    is True
                    for call in calls
                ),
            )
        )

        tests.append(
            (
                "Persisted READY_NO_SUBMIT is marked IN_PROGRESS",
                (
                    "job-one"
                    in marked
                    and report[
                        "results"
                    ][
                        0
                    ][
                        "application_status_after"
                    ]
                    == "IN_PROGRESS"
                ),
            )
        )

        tests.append(
            (
                "NEEDS_ASSISTANCE is not marked IN_PROGRESS by queue runner",
                "job-three"
                not in marked,
            )
        )

        serialized = json.dumps(
            report
        )

        tests.append(
            (
                "Queue report does not contain applicant profile PII",
                (
                    "PrivateFirst"
                    not in serialized
                    and "private@example.com"
                    not in serialized
                    and "1 Private Street"
                    not in serialized
                ),
            )
        )

        no_persist_repo = (
            make_repository()
        )

        add_candidate(
            no_persist_repo,
            suffix="dry",
        )

        dry_marked = []

        no_persist_repo.mark_browser_ready_no_submit = (
            lambda *,
            job_id: (
                dry_marked.append(
                    job_id
                )
            )
        )

        dry_report = (
            run_browser_queue(
                profile=profile,
                repository=no_persist_repo,
                limit=1,
                artifacts_dir=(
                    directory
                    / "queue-dry"
                ),
                persist=False,
                delay_seconds=0,
                run_id="dry-run",
                orchestrate_fn=(
                    fake_orchestrate
                ),
            )
        )

        tests.append(
            (
                "Default no-persist run makes no queue status marker write",
                (
                    not dry_marked
                    and dry_report[
                        "persist"
                    ]
                    is False
                ),
            )
        )

        empty_repo = (
            make_repository()
        )

        empty_report = (
            run_browser_queue(
                profile=profile,
                repository=empty_repo,
                limit=3,
                artifacts_dir=(
                    directory
                    / "empty"
                ),
                persist=False,
                delay_seconds=0,
                run_id="empty-run",
                orchestrate_fn=(
                    fake_orchestrate
                ),
            )
        )

        tests.append(
            (
                "Empty queue exits cleanly with zero attempted jobs",
                (
                    empty_report[
                        "summary"
                    ][
                        "selected"
                    ]
                    == 0
                    and empty_report[
                        "summary"
                    ][
                        "submitted"
                    ]
                    == 0
                ),
            )
        )

    source = (
        Path(
            __import__(
                "src.browser.queue_runner",
                fromlist=[
                    "dummy"
                ],
            ).__file__
        )
        .read_text(
            encoding="utf-8"
        )
        .lower()
    )

    tests.append(
        (
            "Queue runner contains no submit call path",
            (
                ".click("
                not in source
                and "requestsubmit"
                not in source
                and ".submit("
                not in source
            ),
        )
    )

    print()
    print("=" * 104)
    print(
        "BROWSER QUEUE RUNNER V1 TEST"
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
        "✅ BROWSER QUEUE RUNNER V1 TEST PASSED"
    )
    print("=" * 104)


if __name__ == "__main__":
    main()
