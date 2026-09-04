import json
from pathlib import Path
import tempfile
import types
import sys


# Stub project Supabase helper before repository import.
stub = types.ModuleType(
    "src.database.supabase_client"
)
stub.get_owner_id = lambda: "owner-1"
stub.get_supabase_client = lambda: None
sys.modules[
    "src.database.supabase_client"
] = stub


from src.browser.assistance_handoff import (  # noqa: E402
    build_assistance_handoff,
)
from src.browser.orchestrator import (  # noqa: E402
    _greenhouse_application_url,
    _is_greenhouse_url,
    orchestrate_browser_application,
)
from src.profile.applicant_profile import (  # noqa: E402
    ApplicantProfile,
)


class FakeRepository:
    def __init__(
        self,
        *,
        route="AGENT_APPLY",
        method="AGENT",
        assistance_reason=None,
    ):
        self.route = route
        self.method = method
        self.assistance_reason = (
            assistance_reason
        )
        self.persist_calls = []
        self.assert_calls = 0

    def find_job_id(
        self,
        *,
        board_token,
        greenhouse_job_id,
    ):
        return "job-1"

    def assert_browser_execution_allowed(
        self,
        *,
        job_id,
    ):
        self.assert_calls += 1

        if self.route != "AGENT_APPLY":
            raise RuntimeError(
                "Browser execution blocked: "
                "latest evaluation route must "
                "be AGENT_APPLY."
            )

        if self.method != "AGENT":
            raise RuntimeError(
                "Browser execution blocked: "
                "application_method must be AGENT."
            )

        if (
            self.assistance_reason
            and not self.assistance_reason.startswith(
                "BROWSER:"
            )
        ):
            raise RuntimeError(
                "Browser execution blocked: "
                "non-browser assistance is active."
            )

        return {
            "job": {
                "id": "job-1",
                "board_token": "example",
                "greenhouse_job_id": "123",
                "company": "Example",
                "title": "Software Engineer",
                "url": (
                    "https://careers.example.com/"
                    "roles/software-engineer/123"
                ),
                "is_active": True,
            },
            "evaluation": {
                "route": self.route,
                "selected_resume": (
                    "software_engineer"
                ),
                "selected_resume_file": (
                    "Software_Engineer.pdf"
                ),
                "score": 70,
                "selection_score": 80,
                "confidence": 90,
            },
            "application": {
                "id": "app-1",
                "status": "PENDING",
                "application_method": (
                    self.method
                ),
                "needs_assistance": (
                    bool(
                        self.assistance_reason
                    )
                ),
                "assistance_reason": (
                    self.assistance_reason
                ),
            },
        }

    def sync_browser_assistance_handoff(
        self,
        *,
        job_id,
        handoff,
    ):
        if self.route != "AGENT_APPLY":
            raise RuntimeError(
                "Browser handoff persistence blocked."
            )

        self.persist_calls.append(
            handoff
        )

        return "app-1"


def make_profile(
    directory: Path,
):
    payload = {
        "profile_version": 1,
        "identity": {
            "first_name": "Test",
            "last_name": "Applicant",
            "preferred_first_name": "Test",
        },
        "contact": {
            "email": "test@example.com",
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
            "street_address": "1 Test Street",
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


def inspection_result(
    *,
    final_url=(
        "https://job-boards."
        "greenhouse.io/example/"
        "jobs/123"
    ),
):
    return {
        "requested_url": (
            "https://job-boards."
            "greenhouse.io/example/"
            "jobs/123"
        ),
        "final_url": final_url,
        "page_title": (
            "Job Application for "
            "Software Engineer at Example"
        ),
        "form_frame_url": final_url,
        "submit_attempted": False,
        "fields": [
            {
                "label": "First Name*",
                "required": True,
                "decision": {
                    "category": "FIRST_NAME",
                    "action": "PROFILE_VALUE",
                    "answer_key": "FIRST_NAME",
                    "fixed_answer": None,
                    "reason": "test",
                },
            },
            {
                "label": (
                    "Are you legally authorized "
                    "to work in the US?*"
                ),
                "required": True,
                "decision": {
                    "category": (
                        "WORK_AUTHORIZATION_US"
                    ),
                    "action": "FIXED_ANSWER",
                    "answer_key": (
                        "WORK_AUTHORIZED_US"
                    ),
                    "fixed_answer": "Yes",
                    "reason": "test",
                },
            },
            {
                "label": (
                    "How did you hear about us?*"
                ),
                "required": True,
                "decision": {
                    "category": (
                        "APPLICATION_SOURCE"
                    ),
                    "action": "NEEDS_ASSISTANCE",
                    "answer_key": None,
                    "fixed_answer": None,
                    "reason": "test",
                },
            },
        ],
    }


def challenge_fill(
    **_kwargs,
):
    return {
        "requested_url": "x",
        "final_url": "x",
        "fill_results": [],
        "fill_summary": {
            "tasks_attempted": 0,
            "filled": 0,
            "fill_failed": 0,
            "browser_modified": False,
            "submit_attempts_blocked": 0,
            "submit_clicked_by_agent": False,
            "application_submitted": False,
            "page_challenge_detected": True,
            "page_challenge_reasons": [
                "reCAPTCHA iframe",
            ],
            "mutation_blocked_by_challenge": True,
            "nonready_mutation_detected": False,
            "nonready_mutation_reason": "",
        },
    }


def success_fill(
    **_kwargs,
):
    return {
        "requested_url": "x",
        "final_url": "x",
        "fill_results": [
            {
                "label": "First Name*",
                "category": "FIRST_NAME",
                "answer_key": "FIRST_NAME",
                "required": True,
                "status": "FILLED",
                "operation": "FILL_VALUE",
                "source": "profile",
                "reason": "ok",
            },
            {
                "label": (
                    "Are you legally authorized "
                    "to work in the US?*"
                ),
                "category": (
                    "WORK_AUTHORIZATION_US"
                ),
                "answer_key": (
                    "WORK_AUTHORIZED_US"
                ),
                "required": True,
                "status": "FILLED",
                "operation": "FILL_VALUE",
                "source": "fixed_policy",
                "reason": "ok",
            },
        ],
        "fill_summary": {
            "tasks_attempted": 2,
            "filled": 2,
            "fill_failed": 0,
            "browser_modified": True,
            "submit_attempts_blocked": 0,
            "submit_clicked_by_agent": False,
            "application_submitted": False,
            "page_challenge_detected": False,
            "page_challenge_reasons": [],
            "mutation_blocked_by_challenge": False,
            "nonready_mutation_detected": False,
            "nonready_mutation_reason": "",
        },
    }


def failed_fill(
    **_kwargs,
):
    result = success_fill()
    result[
        "fill_results"
    ][
        0
    ][
        "status"
    ] = "FILL_FAILED"
    result[
        "fill_results"
    ][
        0
    ][
        "reason"
    ] = "DOM changed."
    result[
        "fill_summary"
    ][
        "filled"
    ] = 1
    result[
        "fill_summary"
    ][
        "fill_failed"
    ] = 1
    return result


def main():
    tests = []

    tests.append(
        (
            "Approved Greenhouse host accepted",
            _is_greenhouse_url(
                "https://job-boards.greenhouse.io/x/jobs/1"
            ),
        )
    )

    tests.append(
        (
            "Non-Greenhouse host rejected",
            not _is_greenhouse_url(
                "https://example.com/jobs/1"
            ),
        )
    )

    tests.append(
        (
            "Canonical Greenhouse application URL is derived from board + job id",
            _greenhouse_application_url(
                board_token="stripe",
                greenhouse_job_id="6042172",
            )
            == (
                "https://job-boards.greenhouse.io/"
                "embed/job_app?for=stripe&token=6042172"
            ),
        )
    )

    invalid_board_blocked = False

    try:
        _greenhouse_application_url(
            board_token="stripe/../../evil",
            greenhouse_job_id="6042172",
        )
    except RuntimeError:
        invalid_board_blocked = True

    tests.append(
        (
            "Invalid Greenhouse board token fails closed",
            invalid_board_blocked,
        )
    )

    with tempfile.TemporaryDirectory() as raw:
        directory = Path(
            raw
        )
        profile = make_profile(
            directory
        )

        resume_dir = (
            directory
            / "resumes"
        )
        resume_dir.mkdir()

        (
            resume_dir
            / "Software_Engineer.pdf"
        ).write_bytes(
            b"%PDF-test"
        )

        artifacts = (
            directory
            / "artifacts"
        )

        custom_repo = FakeRepository()
        inspected_urls = []

        def capture_inspection_url(
            *,
            url,
            headless,
        ):
            inspected_urls.append(
                url
            )
            return inspection_result(
                final_url=url
            )

        custom_result = (
            orchestrate_browser_application(
                board_token="example",
                greenhouse_job_id="123",
                profile=profile,
                resume_dir=resume_dir,
                artifacts_dir=(
                    directory
                    / "custom-url"
                ),
                headless=True,
                persist=False,
                repository=custom_repo,
                inspect_fn=capture_inspection_url,
                fill_fn=challenge_fill,
            )
        )

        tests.append(
            (
                "Custom stored careers URL routes browser to Greenhouse application form",
                (
                    inspected_urls
                    == [
                        (
                            "https://job-boards.greenhouse.io/"
                            "embed/job_app?for=example&token=123"
                        )
                    ]
                    and custom_result[
                        "stored_job_url_host"
                    ]
                    == "careers.example.com"
                    and custom_result[
                        "application_url_host"
                    ]
                    == "job-boards.greenhouse.io"
                ),
            )
        )

        repo = FakeRepository()

        result = (
            orchestrate_browser_application(
                board_token="example",
                greenhouse_job_id="123",
                profile=profile,
                resume_dir=resume_dir,
                artifacts_dir=artifacts,
                headless=True,
                persist=True,
                repository=repo,
                inspect_fn=lambda **_kwargs: (
                    inspection_result()
                ),
                fill_fn=challenge_fill,
            )
        )

        tests.append(
            (
                "CAPTCHA produces zero-mutation assistance outcome",
                (
                    result[
                        "outcome"
                    ]
                    == "NEEDS_ASSISTANCE"
                    and result[
                        "challenge_detected"
                    ]
                    is True
                    and result[
                        "filled"
                    ]
                    == 0
                    and len(
                        repo.persist_calls
                    )
                    == 1
                ),
            )
        )

        tests.append(
            (
                "Route is checked before inspection and before fill",
                repo.assert_calls
                >= 2,
            )
        )

        handoff = (
            repo.persist_calls[
                0
            ]
        )

        tests.append(
            (
                "Required human question survives CAPTCHA handoff",
                handoff[
                    "summary"
                ][
                    "required_human_count"
                ]
                == 1,
            )
        )

        tests.append(
            (
                "No applicant PII is written to orchestration result",
                "Test"
                not in json.dumps(
                    result
                ),
            )
        )

        # Challenge-free form with a required custom question
        # can fill deterministic fields but still routes assistance.
        repo = FakeRepository()

        result = (
            orchestrate_browser_application(
                board_token="example",
                greenhouse_job_id="123",
                profile=profile,
                resume_dir=resume_dir,
                artifacts_dir=(
                    directory
                    / "artifacts2"
                ),
                persist=True,
                repository=repo,
                inspect_fn=lambda **_kwargs: (
                    inspection_result()
                ),
                fill_fn=success_fill,
            )
        )

        tests.append(
            (
                "Deterministic fill can occur while human fields stay assistance",
                (
                    result[
                        "filled"
                    ]
                    == 2
                    and result[
                        "outcome"
                    ]
                    == "NEEDS_ASSISTANCE"
                ),
            )
        )

        # Fill failure is removed from ready and becomes assistance.
        repo = FakeRepository()

        result = (
            orchestrate_browser_application(
                board_token="example",
                greenhouse_job_id="123",
                profile=profile,
                resume_dir=resume_dir,
                artifacts_dir=(
                    directory
                    / "artifacts3"
                ),
                persist=True,
                repository=repo,
                inspect_fn=lambda **_kwargs: (
                    inspection_result()
                ),
                fill_fn=failed_fill,
            )
        )

        failed_handoff = (
            repo.persist_calls[
                0
            ]
        )

        tests.append(
            (
                "Browser fill failure forces assistance",
                (
                    result[
                        "fill_failed"
                    ]
                    == 1
                    and result[
                        "outcome"
                    ]
                    == "NEEDS_ASSISTANCE"
                    and any(
                        item.get(
                            "status"
                        )
                        == "FILL_FAILED"
                        for item in failed_handoff[
                            "human_assistance"
                        ]
                    )
                ),
            )
        )

        tests.append(
            (
                "Failed deterministic field is not still shown ready",
                not any(
                    item.get(
                        "answer_key"
                    )
                    == "FIRST_NAME"
                    for item in failed_handoff[
                        "deterministic_ready"
                    ]
                ),
            )
        )

        # Redirect outside Greenhouse: inspection allowed,
        # browser mutation skipped, assistance persisted.
        repo = FakeRepository()

        fill_called = {
            "value": False,
        }

        def should_not_fill(
            **_kwargs,
        ):
            fill_called[
                "value"
            ] = True
            raise AssertionError(
                "fill should not run"
            )

        result = (
            orchestrate_browser_application(
                board_token="example",
                greenhouse_job_id="123",
                profile=profile,
                resume_dir=resume_dir,
                artifacts_dir=(
                    directory
                    / "artifacts4"
                ),
                persist=True,
                repository=repo,
                inspect_fn=lambda **_kwargs: (
                    inspection_result(
                        final_url=(
                            "https://example.com/"
                            "redirected"
                        )
                    )
                ),
                fill_fn=should_not_fill,
            )
        )

        tests.append(
            (
                "Off-Greenhouse redirect blocks all mutation",
                (
                    fill_called[
                        "value"
                    ]
                    is False
                    and result[
                        "browser_modified"
                    ]
                    is False
                    and result[
                        "outcome"
                    ]
                    == "NEEDS_ASSISTANCE"
                ),
            )
        )

        # No-persist mode is useful for local production smoke tests.
        repo = FakeRepository()

        result = (
            orchestrate_browser_application(
                board_token="example",
                greenhouse_job_id="123",
                profile=profile,
                resume_dir=resume_dir,
                artifacts_dir=(
                    directory
                    / "artifacts5"
                ),
                persist=False,
                repository=repo,
                inspect_fn=lambda **_kwargs: (
                    inspection_result()
                ),
                fill_fn=challenge_fill,
            )
        )

        tests.append(
            (
                "No-persist mode performs zero Supabase handoff writes",
                (
                    result[
                        "persisted"
                    ]
                    is False
                    and not repo.persist_calls
                ),
            )
        )

        # Non-agent route blocks before the read-only browser opens.
        repo = FakeRepository(
            route="MANUAL_PRIORITY"
        )

        inspect_called = {
            "value": False,
        }

        def should_not_inspect(
            **_kwargs,
        ):
            inspect_called[
                "value"
            ] = True
            return inspection_result()

        blocked = False

        try:
            orchestrate_browser_application(
                board_token="example",
                greenhouse_job_id="123",
                profile=profile,
                resume_dir=resume_dir,
                artifacts_dir=(
                    directory
                    / "artifacts6"
                ),
                persist=True,
                repository=repo,
                inspect_fn=should_not_inspect,
                fill_fn=challenge_fill,
            )
        except RuntimeError:
            blocked = True

        tests.append(
            (
                "MANUAL_PRIORITY route blocks before browser open",
                (
                    blocked
                    and inspect_called[
                        "value"
                    ]
                    is False
                ),
            )
        )

        # Existing non-browser assistance blocks browser execution.
        repo = FakeRepository(
            assistance_reason=(
                "ELIGIBILITY: SECURITY_CLEARANCE"
            )
        )

        blocked = False

        try:
            orchestrate_browser_application(
                board_token="example",
                greenhouse_job_id="123",
                profile=profile,
                resume_dir=resume_dir,
                artifacts_dir=(
                    directory
                    / "artifacts7"
                ),
                persist=True,
                repository=repo,
                inspect_fn=lambda **_kwargs: (
                    inspection_result()
                ),
                fill_fn=challenge_fill,
            )
        except RuntimeError:
            blocked = True

        tests.append(
            (
                "Eligibility assistance blocks Browser Agent execution",
                blocked,
            )
        )

        # Missing selected resume blocks before browser.
        (
            resume_dir
            / "Software_Engineer.pdf"
        ).unlink()

        repo = FakeRepository()

        inspect_called = {
            "value": False,
        }

        blocked = False

        try:
            orchestrate_browser_application(
                board_token="example",
                greenhouse_job_id="123",
                profile=profile,
                resume_dir=resume_dir,
                artifacts_dir=(
                    directory
                    / "artifacts8"
                ),
                persist=True,
                repository=repo,
                inspect_fn=should_not_inspect,
                fill_fn=challenge_fill,
            )
        except RuntimeError:
            blocked = True

        tests.append(
            (
                "Missing matcher-selected resume blocks before browser",
                (
                    blocked
                    and inspect_called[
                        "value"
                    ]
                    is False
                ),
            )
        )

    source = (
        Path(
            __import__(
                "src.browser.orchestrator",
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
            "Orchestrator contains no submit call path",
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
    print("=" * 96)
    print(
        "BROWSER ORCHESTRATOR V1.1 TEST"
    )
    print("=" * 96)
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
    print("=" * 96)
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
        "✅ BROWSER ORCHESTRATOR V1.1 TEST PASSED"
    )
    print("=" * 96)


if __name__ == "__main__":
    main()
