import json
from pathlib import Path
import tempfile

from src.profile.applicant_profile import (
    ApplicantProfile,
)
from src.profile.value_resolver import (
    STATUS_MISSING_RESUME,
    STATUS_OPTIONAL_MISSING,
    STATUS_POLICY_MISMATCH,
    STATUS_READY,
    STATUS_REQUIRED_ASSISTANCE,
    resolve_application,
    resolve_field,
)


def make_profile(
    directory: Path,
    *,
    sponsorship_future: bool = True,
) -> ApplicantProfile:
    data = {
        "profile_version": 1,
        "identity": {
            "first_name": "Test",
            "last_name": "Applicant",
            "preferred_first_name": None,
        },
        "contact": {
            "email": "test@example.com",
            "phone": "+1-555-0100",
        },
        "links": {
            "linkedin_url": "https://example.com/linkedin",
            "portfolio_url": None,
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
            "degree": "Master's",
            "discipline": "Information Systems",
        },
        "work_authorization": {
            "authorized_to_work_us": True,
            "sponsorship_now": False,
            "sponsorship_future": sponsorship_future,
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


def make_field(
    *,
    label: str,
    category: str,
    action: str,
    answer_key: str | None,
    required: bool = True,
    fixed_answer: str | None = None,
) -> dict:
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

        resume = directory / "resume.pdf"
        resume.write_bytes(
            b"%PDF-test"
        )

        # 1. Standard profile value.
        result = resolve_field(
            field=make_field(
                label="First Name",
                category="FIRST_NAME",
                action="PROFILE_VALUE",
                answer_key="FIRST_NAME",
            ),
            profile=profile,
        )
        tests.append(
            (
                "First name resolves",
                result.status == STATUS_READY
                and result.value == "Test",
            )
        )

        # 2. Current US location bool -> Yes.
        result = resolve_field(
            field=make_field(
                label="Currently in US",
                category="CURRENT_US_LOCATION",
                action="PROFILE_VALUE",
                answer_key="CURRENT_US_LOCATION",
            ),
            profile=profile,
        )
        tests.append(
            (
                "Current US location resolves to Yes",
                result.status == STATUS_READY
                and result.value == "Yes",
            )
        )

        # 3. Current sponsorship.
        result = resolve_field(
            field=make_field(
                label="Current sponsorship",
                category="SPONSORSHIP_NOW",
                action="FIXED_ANSWER",
                answer_key="SPONSORSHIP_NOW",
                fixed_answer="No",
            ),
            profile=profile,
        )
        tests.append(
            (
                "Current sponsorship resolves from profile",
                result.status == STATUS_READY
                and result.value == "No",
            )
        )

        # 4. Combined now/future sponsorship.
        result = resolve_field(
            field=make_field(
                label="Now or future sponsorship",
                category="SPONSORSHIP_NOW_OR_FUTURE",
                action="FIXED_ANSWER",
                answer_key="SPONSORSHIP_NOW_OR_FUTURE",
                fixed_answer="Yes",
            ),
            profile=profile,
        )
        tests.append(
            (
                "Now-or-future sponsorship resolves to Yes",
                result.status == STATUS_READY
                and result.value == "Yes",
            )
        )

        # 5. Stale classifier hint is caught.
        result = resolve_field(
            field=make_field(
                label="Future sponsorship",
                category="SPONSORSHIP_FUTURE",
                action="FIXED_ANSWER",
                answer_key="SPONSORSHIP_FUTURE",
                fixed_answer="No",
            ),
            profile=profile,
        )
        tests.append(
            (
                "Policy mismatch is blocked",
                result.status == STATUS_POLICY_MISMATCH,
            )
        )

        # 6. Resume exists.
        result = resolve_field(
            field=make_field(
                label="Resume",
                category="RESUME",
                action="RESUME_FILE",
                answer_key="SELECTED_RESUME_FILE",
                required=False,
            ),
            profile=profile,
            resume_path=resume,
        )
        tests.append(
            (
                "Selected resume file resolves",
                result.status == STATUS_READY
                and result.value is not None,
            )
        )

        # 7. Missing resume blocks.
        result = resolve_field(
            field=make_field(
                label="Resume",
                category="RESUME",
                action="RESUME_FILE",
                answer_key="SELECTED_RESUME_FILE",
                required=False,
            ),
            profile=profile,
            resume_path=None,
        )
        tests.append(
            (
                "Missing resume blocks",
                result.status == STATUS_MISSING_RESUME,
            )
        )

        # 8. Optional portfolio can remain missing.
        result = resolve_field(
            field=make_field(
                label="Website",
                category="PORTFOLIO",
                action="PROFILE_VALUE",
                answer_key="PORTFOLIO_URL",
                required=False,
            ),
            profile=profile,
        )
        tests.append(
            (
                "Optional missing profile value stays optional",
                result.status == STATUS_OPTIONAL_MISSING,
            )
        )

        # 9. Required assistance blocks submission readiness.
        inspection = {
            "fields": [
                make_field(
                    label="First Name",
                    category="FIRST_NAME",
                    action="PROFILE_VALUE",
                    answer_key="FIRST_NAME",
                    required=True,
                ),
                make_field(
                    label="Why us?",
                    category="FREEFORM_APPLICATION_QUESTION",
                    action="NEEDS_ASSISTANCE",
                    answer_key=None,
                    required=True,
                ),
            ]
        }

        plan = resolve_application(
            inspection=inspection,
            profile=profile,
            resume_path=resume,
        )

        tests.append(
            (
                "Required assistance blocks submission",
                plan[
                    "summary"
                ][
                    "ready_for_submission"
                ]
                is False
                and plan[
                    "summary"
                ][
                    "required_unresolved"
                ]
                == 1,
            )
        )

        # 10. Optional assistance does not block submission.
        inspection = {
            "fields": [
                make_field(
                    label="First Name",
                    category="FIRST_NAME",
                    action="PROFILE_VALUE",
                    answer_key="FIRST_NAME",
                    required=True,
                ),
                make_field(
                    label="Cover Letter",
                    category="COVER_LETTER_UPLOAD",
                    action="NEEDS_ASSISTANCE",
                    answer_key=None,
                    required=False,
                ),
            ]
        }

        plan = resolve_application(
            inspection=inspection,
            profile=profile,
            resume_path=resume,
        )

        tests.append(
            (
                "Optional assistance does not block submission readiness",
                plan[
                    "summary"
                ][
                    "ready_for_submission"
                ]
                is True,
            )
        )

        # 11. Public report redacts sensitive value.
        result = resolve_field(
            field=make_field(
                label="Email",
                category="EMAIL",
                action="PROFILE_VALUE",
                answer_key="EMAIL",
            ),
            profile=profile,
        )

        public = result.public_dict(
            include_values=False
        )

        tests.append(
            (
                "Sensitive value is redacted in public report",
                public.get(
                    "value_preview"
                )
                == "<redacted>"
                and "value"
                not in public,
            )
        )

        # 12. Full name is derived, not separately stored.
        result = resolve_field(
            field=make_field(
                label="Full Name",
                category="FULL_NAME",
                action="PROFILE_VALUE",
                answer_key="FULL_NAME",
            ),
            profile=profile,
        )

        tests.append(
            (
                "Full name is safely derived",
                result.status == STATUS_READY
                and result.value == "Test Applicant",
            )
        )

    print()
    print("=" * 90)
    print(
        "APPLICANT PROFILE + SAFE VALUE RESOLVER V1 TEST"
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
        marker = (
            "✅ PASS"
            if ok
            else "❌ FAIL"
        )

        print(
            f"{index:02}. "
            f"{marker} — "
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
        "✅ APPLICANT PROFILE + SAFE VALUE RESOLVER "
        "V1 TEST PASSED"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
