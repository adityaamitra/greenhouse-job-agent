import json
from pathlib import Path
import tempfile

from src.browser.assistance_handoff import (
    ROUTE_AGENT_CONTINUE,
    ROUTE_NEEDS_ASSISTANCE,
    build_assistance_handoff,
    render_handoff_markdown,
)
from src.profile.applicant_profile import (
    ApplicantProfile,
)


def make_profile(
    directory: Path,
) -> ApplicantProfile:
    data = {
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
            "linkedin_url": "https://example.com/linkedin",
            "portfolio_url": "https://example.com/portfolio",
            "github_url": "https://example.com/github",
        },
        "address": {
            "country": "United States",
            "city": "Boston",
            "state_or_province": "MA",
            "postal_code": "00000",
            "street_address": "1 Example Street",
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
            data
        ),
        encoding="utf-8",
    )

    return ApplicantProfile.load(
        path
    )


def field(
    *,
    label,
    category,
    action,
    answer_key=None,
    required=True,
    fixed_answer=None,
):
    return {
        "label": label,
        "required": required,
        "decision": {
            "category": category,
            "action": action,
            "answer_key": answer_key,
            "fixed_answer": fixed_answer,
            "reason": "synthetic",
        },
    }


def main():
    tests = []

    with tempfile.TemporaryDirectory() as raw_dir:
        directory = Path(
            raw_dir
        )

        profile = make_profile(
            directory
        )

        resume = directory / "Software_Engineer.pdf"
        resume.write_bytes(
            b"%PDF-test"
        )

        base_inspection = {
            "requested_url": "https://job-boards.greenhouse.io/example/jobs/1",
            "page_title": "Job Application for Software Engineer at Example Co",
            "fields": [
                field(
                    label="First Name*",
                    category="FIRST_NAME",
                    action="PROFILE_VALUE",
                    answer_key="FIRST_NAME",
                ),
                field(
                    label="Are you legally authorized to work in the US?*",
                    category="WORK_AUTHORIZATION_US",
                    action="FIXED_ANSWER",
                    answer_key="WORK_AUTHORIZED_US",
                    fixed_answer="Yes",
                ),
                field(
                    label="Will you now or in the future require sponsorship?*",
                    category="SPONSORSHIP_NOW_OR_FUTURE",
                    action="FIXED_ANSWER",
                    answer_key="SPONSORSHIP_NOW_OR_FUTURE",
                    fixed_answer="Yes",
                ),
                field(
                    label="How did you hear about us?*",
                    category="APPLICATION_SOURCE",
                    action="NEEDS_ASSISTANCE",
                    required=True,
                ),
                field(
                    label="Gender",
                    category="VOLUNTARY_DEMOGRAPHIC",
                    action="NEEDS_ASSISTANCE",
                    required=False,
                ),
            ],
        }

        packet = build_assistance_handoff(
            inspection=base_inspection,
            profile=profile,
            resume_path=resume,
        )

        tests.append(
            (
                "Required custom question routes to assistance",
                packet[
                    "route"
                ]
                == ROUTE_NEEDS_ASSISTANCE,
            )
        )

        tests.append(
            (
                "Company and job parse from Greenhouse title",
                (
                    packet[
                        "company"
                    ]
                    == "Example Co"
                    and packet[
                        "job_title"
                    ]
                    == "Software Engineer"
                ),
            )
        )

        policy_answers = {
            item[
                "answer_key"
            ]: item[
                "display_answer"
            ]
            for item in packet[
                "deterministic_ready"
            ]
            if item[
                "answer_key"
            ]
        }

        tests.append(
            (
                "Work authorization policy answer is visible",
                policy_answers.get(
                    "WORK_AUTHORIZED_US"
                )
                == "Yes",
            )
        )

        tests.append(
            (
                "Now/future sponsorship policy answer is visible",
                policy_answers.get(
                    "SPONSORSHIP_NOW_OR_FUTURE"
                )
                == "Yes",
            )
        )

        profile_ready = next(
            item
            for item in packet[
                "deterministic_ready"
            ]
            if item[
                "answer_key"
            ]
            == "FIRST_NAME"
        )

        tests.append(
            (
                "PII profile value is not exposed",
                profile_ready[
                    "display_answer"
                ]
                is None,
            )
        )

        fill_report = {
            "fill_summary": {
                "page_challenge_detected": True,
                "page_challenge_reasons": [
                    "reCAPTCHA iframe: 1 element(s), 1 visible",
                ],
                "nonready_mutation_detected": False,
                "nonready_mutation_reason": "",
            }
        }

        packet = build_assistance_handoff(
            inspection=base_inspection,
            profile=profile,
            resume_path=resume,
            fill_report=fill_report,
        )

        tests.append(
            (
                "CAPTCHA challenge is surfaced",
                (
                    packet[
                        "challenge"
                    ][
                        "detected"
                    ]
                    is True
                    and packet[
                        "route"
                    ]
                    == ROUTE_NEEDS_ASSISTANCE
                ),
            )
        )

        markdown = render_handoff_markdown(
            packet
        )

        tests.append(
            (
                "Markdown includes safety status and challenge",
                (
                    "CAPTCHA / anti-bot challenge detected"
                    in markdown
                    and "Application submitted: **NO**"
                    in markdown
                ),
            )
        )

        clean_inspection = {
            "requested_url": "https://job-boards.greenhouse.io/example/jobs/2",
            "page_title": "Job Application for Backend Engineer at Example Co",
            "fields": [
                field(
                    label="First Name*",
                    category="FIRST_NAME",
                    action="PROFILE_VALUE",
                    answer_key="FIRST_NAME",
                ),
                field(
                    label="Resume",
                    category="RESUME",
                    action="RESUME_FILE",
                    answer_key="SELECTED_RESUME_FILE",
                    required=False,
                ),
            ],
        }

        packet = build_assistance_handoff(
            inspection=clean_inspection,
            profile=profile,
            resume_path=resume,
        )

        tests.append(
            (
                "Challenge-free fully deterministic application can continue",
                packet[
                    "route"
                ]
                == ROUTE_AGENT_CONTINUE,
            )
        )

        tests.append(
            (
                "Only resume basename is exposed",
                packet[
                    "selected_resume"
                ]
                == "Software_Engineer.pdf",
            )
        )

    print()
    print("=" * 90)
    print(
        "BROWSER ASSISTANCE HANDOFF V1 TEST"
    )
    print("=" * 90)
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
    print("=" * 90)
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
        "✅ BROWSER ASSISTANCE HANDOFF V1 TEST PASSED"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
