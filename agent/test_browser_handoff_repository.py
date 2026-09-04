import sys
import types


# repository.py imports the real project Supabase helper.
# Synthetic tests provide a stub before importing repository.py.
stub = types.ModuleType(
    "src.database.supabase_client"
)

stub.get_owner_id = lambda: "owner-1"
stub.get_supabase_client = lambda: None

sys.modules[
    "src.database.supabase_client"
] = stub


from src.database.repository import (  # noqa: E402
    BROWSER_ROUTE_AGENT_CONTINUE,
    BROWSER_ROUTE_NEEDS_ASSISTANCE,
    JobRepository,
    build_browser_assistance_question,
    build_browser_assistance_reason,
    sanitize_browser_handoff,
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
        self.operation = "select"
        return self

    def insert(
        self,
        payload,
    ):
        self.operation = "insert"
        self.payload = dict(
            payload
        )
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
                "__IN__",
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
        for item in self.filters:
            if (
                len(
                    item
                )
                == 3
                and item[
                    0
                ]
                == "__IN__"
            ):
                _, key, values = item

                if row.get(
                    key
                ) not in values:
                    return False

                continue

            key, value = item

            if row.get(
                key
            ) != value:
                return False

        return True

    def execute(
        self,
    ):
        rows = self.client.tables[
            self.table_name
        ]

        if self.operation == "select":
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

        if self.operation == "insert":
            row = dict(
                self.payload
            )

            if "id" not in row:
                row[
                    "id"
                ] = (
                    f"{self.table_name}-"
                    f"{len(rows) + 1}"
                )

            rows.append(
                row
            )

            return FakeResponse(
                [
                    dict(
                        row
                    )
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

        raise AssertionError(
            self.operation
        )


class FakeClient:
    def __init__(
        self,
    ):
        self.tables = {
            "jobs": [],
            "job_evaluations": [],
            "agent_runs": [],
            "applications": [],
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


def make_packet(
    *,
    route=(
        BROWSER_ROUTE_NEEDS_ASSISTANCE
    ),
    challenge=True,
    required=2,
):
    human = [
        {
            "label": (
                f"Question {index + 1}"
            ),
            "category": (
                "UNKNOWN_CUSTOM_FIELD"
            ),
            "required": True,
            "status": (
                "REQUIRED_ASSISTANCE"
            ),
            "source": "human",
            "answer_key": None,
            "display_answer": None,
            "reason": "Human review.",
        }
        for index in range(
            required
        )
    ]

    return {
        "packet_version": 1,
        "company": "Example",
        "job_title": "Software Engineer",
        "requested_url": (
            "https://job-boards.greenhouse.io/"
            "example/jobs/1"
        ),
        "page_title": (
            "Job Application for Software "
            "Engineer at Example"
        ),
        "selected_resume": (
            "/private/local/path/"
            "Software_Engineer.pdf"
        ),
        "route": route,
        "route_reasons": [
            "Page challenge / CAPTCHA detected."
        ]
        if challenge
        else [],
        "challenge": {
            "detected": challenge,
            "reasons": [
                "reCAPTCHA iframe"
            ]
            if challenge
            else [],
        },
        "browser_safety": {
            "application_submitted": False,
            "submit_clicked_by_agent": False,
            "nonready_mutation_detected": False,
            "nonready_mutation_reason": "",
        },
        "deterministic_ready": [
            {
                "label": "First Name*",
                "category": "FIRST_NAME",
                "required": True,
                "status": "READY",
                "source": "profile",
                "answer_key": "FIRST_NAME",
                # Deliberately unsafe input:
                "display_answer": "SecretName",
                "reason": "Profile value.",
            },
            {
                "label": (
                    "Are you legally authorized "
                    "to work in the US?*"
                ),
                "category": (
                    "WORK_AUTHORIZATION_US"
                ),
                "required": True,
                "status": "READY",
                "source": "fixed_policy",
                "answer_key": (
                    "WORK_AUTHORIZED_US"
                ),
                "display_answer": "Yes",
                "reason": "Policy.",
            },
        ],
        "human_assistance": human,
        "summary": {
            "ready_count": 999,
            "human_assistance_count": 999,
            "required_human_count": 999,
            "challenge_detected": challenge,
            "policy_mismatches": 0,
            "missing_resume": 0,
        },
    }


def make_repository(
    *,
    route="AGENT_APPLY",
    job_id="job-1",
):
    repository = object.__new__(
        JobRepository
    )

    repository.client = (
        FakeClient()
    )

    repository.owner_id = (
        "owner-1"
    )

    if route is not None:
        repository.client.tables[
            "job_evaluations"
        ].append(
            {
                "owner_id": "owner-1",
                "job_id": job_id,
                "run_id": "run-latest",
                "route": route,
            }
        )

        repository.client.tables[
            "agent_runs"
        ].append(
            {
                "id": "run-latest",
                "owner_id": "owner-1",
                "completed_at": "2026-09-04T12:00:00+00:00",
            }
        )

    return repository


def main():
    tests = []

    packet = sanitize_browser_handoff(
        make_packet()
    )

    tests.append(
        (
            "Resume path is reduced to basename",
            packet[
                "selected_resume"
            ]
            == "Software_Engineer.pdf",
        )
    )

    first_name = packet[
        "deterministic_ready"
    ][
        0
    ]

    tests.append(
        (
            "Unsafe profile display value is redacted",
            first_name[
                "display_answer"
            ]
            is None,
        )
    )

    work_auth = packet[
        "deterministic_ready"
    ][
        1
    ]

    tests.append(
        (
            "Approved policy Yes/No remains visible",
            work_auth[
                "display_answer"
            ]
            == "Yes",
        )
    )

    tests.append(
        (
            "Summary counts are recomputed",
            (
                packet[
                    "summary"
                ][
                    "ready_count"
                ]
                == 2
                and packet[
                    "summary"
                ][
                    "required_human_count"
                ]
                == 2
            ),
        )
    )

    reason = (
        build_browser_assistance_reason(
            packet
        )
    )

    tests.append(
        (
            "Compact reason includes CAPTCHA and count",
            (
                "CAPTCHA"
                in reason
                and "REQUIRED_QUESTIONS=2"
                in reason
            ),
        )
    )

    question = (
        build_browser_assistance_question(
            packet
        )
    )

    tests.append(
        (
            "Human question summarizes ready and required counts",
            (
                "2 required"
                in question
                and "2 deterministic"
                in question
            ),
        )
    )

    repository = make_repository()

    repository.client.tables[
        "jobs"
    ].append(
        {
            "id": "job-1",
            "owner_id": "owner-1",
            "board_token": "example",
            "greenhouse_job_id": "123",
        }
    )

    tests.append(
        (
            "Greenhouse job lookup resolves internal job id",
            repository.find_job_id(
                board_token="example",
                greenhouse_job_id=123,
            )
            == "job-1",
        )
    )

    application_id = (
        repository
        .sync_browser_assistance_handoff(
            job_id="job-1",
            handoff=packet,
        )
    )

    applications = (
        repository.client.tables[
            "applications"
        ]
    )

    requests = (
        repository.client.tables[
            "assistance_requests"
        ]
    )

    tests.append(
        (
            "Browser assistance creates pending AGENT application",
            (
                len(
                    applications
                )
                == 1
                and applications[
                    0
                ][
                    "application_method"
                ]
                == "AGENT"
                and applications[
                    0
                ][
                    "needs_assistance"
                ]
                is True
                and applications[
                    0
                ][
                    "assistance_reason"
                ].startswith(
                    "BROWSER:"
                )
            ),
        )
    )

    tests.append(
        (
            "Browser request persists sanitized structured handoff",
            (
                len(
                    requests
                )
                == 1
                and requests[
                    0
                ][
                    "source"
                ]
                == "BROWSER"
                and requests[
                    0
                ][
                    "handoff"
                ][
                    "selected_resume"
                ]
                == "Software_Engineer.pdf"
                and requests[
                    0
                ][
                    "handoff"
                ][
                    "deterministic_ready"
                ][
                    0
                ][
                    "display_answer"
                ]
                is None
            ),
        )
    )

    repository.sync_browser_assistance_handoff(
        job_id="job-1",
        handoff=packet,
    )

    tests.append(
        (
            "Repeated sync does not duplicate open browser request",
            len(
                [
                    row
                    for row in requests
                    if (
                        row.get(
                            "source"
                        )
                        == "BROWSER"
                        and row.get(
                            "resolved"
                        )
                        is False
                    )
                ]
            )
            == 1,
        )
    )

    continue_packet = (
        make_packet(
            route=(
                BROWSER_ROUTE_AGENT_CONTINUE
            ),
            challenge=False,
            required=0,
        )
    )

    repository.sync_browser_assistance_handoff(
        job_id="job-1",
        handoff=continue_packet,
    )

    tests.append(
        (
            "AGENT_CONTINUE clears only browser assistance",
            (
                applications[
                    0
                ][
                    "needs_assistance"
                ]
                is False
                and applications[
                    0
                ][
                    "assistance_reason"
                ]
                is None
                and requests[
                    0
                ][
                    "resolved"
                ]
                is True
            ),
        )
    )

    # Eligibility assistance must survive browser AGENT_CONTINUE.
    repository = make_repository(job_id="job-2")

    repository.client.tables[
        "applications"
    ].append(
        {
            "id": "app-eligibility",
            "owner_id": "owner-1",
            "job_id": "job-2",
            "status": "PENDING",
            "application_method": "AGENT",
            "needs_assistance": True,
            "assistance_reason": (
                "ELIGIBILITY: CITIZENSHIP"
            ),
        }
    )

    repository.sync_browser_assistance_handoff(
        job_id="job-2",
        handoff=continue_packet,
    )

    tests.append(
        (
            "Browser continuation never clears eligibility assistance",
            (
                repository.client.tables[
                    "applications"
                ][
                    0
                ][
                    "needs_assistance"
                ]
                is True
                and repository.client.tables[
                    "applications"
                ][
                    0
                ][
                    "assistance_reason"
                ]
                == "ELIGIBILITY: CITIZENSHIP"
            ),
        )
    )

    # Progressed applications stay immutable.
    repository = make_repository(job_id="job-3")

    repository.client.tables[
        "applications"
    ].append(
        {
            "id": "app-submitted",
            "owner_id": "owner-1",
            "job_id": "job-3",
            "status": "SUBMITTED",
            "application_method": "AGENT",
            "needs_assistance": False,
            "assistance_reason": None,
        }
    )

    repository.sync_browser_assistance_handoff(
        job_id="job-3",
        handoff=packet,
    )

    tests.append(
        (
            "Progressed application is never reset",
            (
                repository.client.tables[
                    "applications"
                ][
                    0
                ][
                    "status"
                ]
                == "SUBMITTED"
                and repository.client.tables[
                    "applications"
                ][
                    0
                ][
                    "needs_assistance"
                ]
                is False
                and not repository.client.tables[
                    "assistance_requests"
                ]
            ),
        )
    )

    # Latest matcher route guard.
    repository = make_repository(
        route="MANUAL_PRIORITY",
        job_id="job-manual",
    )

    repository.client.tables[
        "applications"
    ].append(
        {
            "id": "app-manual",
            "owner_id": "owner-1",
            "job_id": "job-manual",
            "status": "PENDING",
            "application_method": "MANUAL",
            "needs_assistance": False,
            "assistance_reason": None,
        }
    )

    blocked = False

    try:
        repository.sync_browser_assistance_handoff(
            job_id="job-manual",
            handoff=packet,
        )
    except RuntimeError as exc:
        blocked = (
            "AGENT_APPLY"
            in str(
                exc
            )
            and "MANUAL_PRIORITY"
            in str(
                exc
            )
        )

    tests.append(
        (
            "MANUAL_PRIORITY job is blocked from browser persistence",
            (
                blocked
                and repository.client.tables[
                    "applications"
                ][
                    0
                ][
                    "needs_assistance"
                ]
                is False
                and not repository.client.tables[
                    "assistance_requests"
                ]
            ),
        )
    )

    repository = make_repository(
        route=None,
        job_id="job-no-eval",
    )

    blocked = False

    try:
        repository.sync_browser_assistance_handoff(
            job_id="job-no-eval",
            handoff=packet,
        )
    except RuntimeError as exc:
        blocked = (
            "found None"
            in str(
                exc
            )
        )

    tests.append(
        (
            "Missing evaluation fails closed",
            blocked,
        )
    )

    repository = make_repository(
        route="AGENT_APPLY",
        job_id="job-agent",
    )

    tests.append(
        (
            "AGENT_APPLY route passes browser guard",
            repository.assert_browser_route_allowed(
                job_id="job-agent",
            )
            == "AGENT_APPLY",
        )
    )

    # Newer route wins over older route.
    repository = make_repository(
        route="AGENT_APPLY",
        job_id="job-switch",
    )

    repository.client.tables[
        "job_evaluations"
    ].append(
        {
            "owner_id": "owner-1",
            "job_id": "job-switch",
            "run_id": "run-old",
            "route": "MANUAL_PRIORITY",
        }
    )

    repository.client.tables[
        "agent_runs"
    ].append(
        {
            "id": "run-old",
            "owner_id": "owner-1",
            "completed_at": "2026-09-03T12:00:00+00:00",
        }
    )

    tests.append(
        (
            "Newest completed evaluation route wins",
            repository.get_latest_evaluation_route(
                job_id="job-switch",
            )
            == "AGENT_APPLY",
        )
    )

    # Browser Orchestrator execution preflight.
    repository = make_repository(
        route="AGENT_APPLY",
        job_id="job-exec",
    )

    repository.client.tables[
        "jobs"
    ].append(
        {
            "id": "job-exec",
            "owner_id": "owner-1",
            "board_token": "example",
            "greenhouse_job_id": "999",
            "company": "Example",
            "title": "Engineer",
            "url": (
                "https://job-boards.greenhouse.io/"
                "example/jobs/999"
            ),
            "is_active": True,
        }
    )

    repository.client.tables[
        "job_evaluations"
    ][
        0
    ].update(
        {
            "selected_resume": "software_engineer",
            "selected_resume_file": (
                "Software_Engineer.pdf"
            ),
            "score": 70,
            "selection_score": 80,
            "confidence": 90,
        }
    )

    repository.client.tables[
        "applications"
    ].append(
        {
            "id": "app-exec",
            "owner_id": "owner-1",
            "job_id": "job-exec",
            "status": "PENDING",
            "application_method": "AGENT",
            "needs_assistance": False,
            "assistance_reason": None,
        }
    )

    execution = (
        repository
        .assert_browser_execution_allowed(
            job_id="job-exec",
        )
    )

    tests.append(
        (
            "Browser execution context accepts valid AGENT_APPLY queue row",
            (
                execution[
                    "job"
                ][
                    "id"
                ]
                == "job-exec"
                and execution[
                    "evaluation"
                ][
                    "selected_resume_file"
                ]
                == "Software_Engineer.pdf"
                and execution[
                    "application"
                ][
                    "application_method"
                ]
                == "AGENT"
            ),
        )
    )

    repository.client.tables[
        "applications"
    ][
        0
    ][
        "needs_assistance"
    ] = True

    repository.client.tables[
        "applications"
    ][
        0
    ][
        "assistance_reason"
    ] = "ELIGIBILITY: SECURITY_CLEARANCE"

    blocked = False

    try:
        repository.assert_browser_execution_allowed(
            job_id="job-exec",
        )
    except RuntimeError:
        blocked = True

    tests.append(
        (
            "Existing eligibility assistance blocks browser execution preflight",
            blocked,
        )
    )

    print()
    print("=" * 94)
    print(
        "SUPABASE BROWSER HANDOFF + ORCHESTRATOR PREFLIGHT TEST"
    )
    print("=" * 94)
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

    failed = len(
        tests
    ) - passed

    print()
    print("=" * 94)
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
        "✅ SUPABASE BROWSER HANDOFF + ORCHESTRATOR PREFLIGHT TEST PASSED"
    )
    print("=" * 94)


if __name__ == "__main__":
    main()
