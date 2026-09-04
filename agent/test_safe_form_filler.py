from dataclasses import dataclass

from src.browser.safe_form_filler import (
    SUBMIT_GUARD_SCRIPT,
    _match_live_field,
    _observable_field_state,
    _option_text_matches,
    build_fill_tasks,
    is_custom_select_candidate,
)


@dataclass
class FakeResolved:
    label: str
    category: str
    answer_key: str | None
    required: bool
    status: str
    source: str
    value: object = None


def field(
    *,
    label,
    action,
    source_count=1,
    source_types=None,
    field_type="text",
):
    return {
        "label": label,
        "type": field_type,
        "source_count": source_count,
        "source_types": (
            source_types
            if source_types is not None
            else [field_type]
        ),
        "decision": {
            "action": action,
        },
    }


def resolved(
    label,
    *,
    status="READY",
    category="TEST",
    key="TEST",
    value="value",
):
    return FakeResolved(
        label=label,
        category=category,
        answer_key=key,
        required=True,
        status=status,
        source="profile",
        value=value,
    )


def main():
    tests = []

    tests.append(
        (
            "Custom two-control text widget is a select candidate",
            is_custom_select_candidate(
                field(
                    label="Country",
                    action="PROFILE_VALUE",
                    source_count=2,
                    source_types=[
                        "text",
                    ],
                )
            ),
        )
    )

    tests.append(
        (
            "Single text field is not treated as custom select",
            not is_custom_select_candidate(
                field(
                    label="First Name",
                    action="PROFILE_VALUE",
                )
            ),
        )
    )

    tasks = build_fill_tasks(
        logical_fields=[
            field(
                label="First Name",
                action="PROFILE_VALUE",
            ),
            field(
                label="Country",
                action="PROFILE_VALUE",
                source_count=2,
                source_types=[
                    "text",
                ],
            ),
            field(
                label="Resume",
                action="RESUME_FILE",
                field_type="file",
            ),
        ],
        resolved_fields=[
            resolved(
                "First Name"
            ),
            resolved(
                "Country"
            ),
            resolved(
                "Resume",
                value="/tmp/resume.pdf",
            ),
        ],
    )

    tests.append(
        (
            "READY deterministic fields become tasks",
            len(
                tasks
            )
            == 3,
        )
    )

    tests.append(
        (
            "Plain profile value uses FILL_VALUE",
            tasks[
                0
            ][
                "operation"
            ]
            == "FILL_VALUE",
        )
    )

    tests.append(
        (
            "Custom select uses SELECT_OPTION",
            tasks[
                1
            ][
                "operation"
            ]
            == "SELECT_OPTION",
        )
    )

    tests.append(
        (
            "Resume uses UPLOAD_RESUME",
            tasks[
                2
            ][
                "operation"
            ]
            == "UPLOAD_RESUME",
        )
    )

    tasks = build_fill_tasks(
        logical_fields=[
            field(
                label="Why us?",
                action="NEEDS_ASSISTANCE",
            ),
            field(
                label="Future sponsorship",
                action="FIXED_ANSWER",
            ),
        ],
        resolved_fields=[
            resolved(
                "Why us?",
                status="REQUIRED_ASSISTANCE",
            ),
            resolved(
                "Future sponsorship",
                status="POLICY_MISMATCH",
            ),
        ],
    )

    tests.append(
        (
            "Assistance and policy mismatch fields are never fill tasks",
            tasks
            == [],
        )
    )

    filler_source = (
        __import__(
            "src.browser.safe_form_filler",
            fromlist=["dummy"],
        )
    )

    source_text = open(
        filler_source.__file__,
        "r",
        encoding="utf-8",
    ).read().lower()

    tests.append(
        (
            "Custom select clicks/focuses before searching options",
            "control.click(" in source_text,
        )
    )

    tests.append(
        (
            "Custom select never uses Enter",
            ".press(" not in source_text
            and "keyboard.press" not in source_text,
        )
    )

    tests.append(
        (
            "Fallback option matching is scoped to popup roots",
            "_custom_select_roots" in source_text
            and "root.get_by_text" in source_text,
        )
    )

    tests.append(
        (
            "Failed dropdown resolution clears input and reports diagnostics",
            "input was cleared" in source_text
            and "visible popup text" in source_text,
        )
    )

    tests.append(
        (
            "COUNTRY accepts exact name plus calling code",
            _option_text_matches(
                field={
                    "decision": {
                        "category": "COUNTRY",
                    }
                },
                desired="United States",
                visible_text="United States +1",
            ),
        )
    )

    tests.append(
        (
            "COUNTRY rejects arbitrary longer country-like text",
            not _option_text_matches(
                field={
                    "decision": {
                        "category": "COUNTRY",
                    }
                },
                desired="United States",
                visible_text="United States Virgin Islands",
            ),
        )
    )

    tests.append(
        (
            "Non-COUNTRY fields do not receive prefix exceptions",
            not _option_text_matches(
                field={
                    "decision": {
                        "category": "CITY",
                    }
                },
                desired="Boston",
                visible_text="Boston +1",
            ),
        )
    )

    planned_phone = {
        "label": "Phone*",
        "type": "tel",
        "dom_indices": [6],
        "decision": {
            "category": "PHONE",
            "action": "PROFILE_VALUE",
            "answer_key": "PHONE",
        },
    }

    live_fields_after_rerender = [
        {
            "label": "Phone*",
            "type": "tel",
            "dom_indices": [5],
            "decision": {
                "category": "PHONE",
                "action": "PROFILE_VALUE",
                "answer_key": "PHONE",
            },
        },
        {
            "label": "Attach",
            "type": "file",
            "dom_indices": [6],
            "decision": {
                "category": "RESUME",
                "action": "RESUME_FILE",
                "answer_key": "SELECTED_RESUME_FILE",
            },
        },
    ]

    rebound, _ = _match_live_field(
        planned_field=planned_phone,
        live_fields=live_fields_after_rerender,
    )

    tests.append(
        (
            "Semantic rebinding ignores stale DOM index drift",
            (
                rebound is not None
                and rebound.get(
                    "dom_indices"
                )
                == [5]
            ),
        )
    )

    planned_website = {
        "label": "Website",
        "type": "text",
        "dom_indices": [10],
        "decision": {
            "category": "PORTFOLIO",
            "action": "PROFILE_VALUE",
            "answer_key": "PORTFOLIO_URL",
        },
    }

    live_fields_with_assistance_neighbor = [
        {
            "label": "Website",
            "type": "text",
            "dom_indices": [9],
            "decision": {
                "category": "PORTFOLIO",
                "action": "PROFILE_VALUE",
                "answer_key": "PORTFOLIO_URL",
            },
        },
        {
            "label": "Are you willing and able to commit to the hybrid policy if hired?*",
            "type": "text",
            "dom_indices": [10, 11],
            "decision": {
                "category": "WORK_LOCATION_COMMITMENT",
                "action": "NEEDS_ASSISTANCE",
                "answer_key": None,
            },
        },
    ]

    rebound, _ = _match_live_field(
        planned_field=planned_website,
        live_fields=live_fields_with_assistance_neighbor,
    )

    tests.append(
        (
            "Website rebind cannot resolve to neighboring assistance field",
            (
                rebound is not None
                and rebound.get(
                    "decision",
                    {}
                ).get(
                    "category"
                )
                == "PORTFOLIO"
                and rebound.get(
                    "dom_indices"
                )
                == [9]
            ),
        )
    )

    ambiguous = [
        dict(
            planned_phone,
            dom_indices=[
                5
            ],
        ),
        dict(
            planned_phone,
            dom_indices=[
                7
            ],
        ),
    ]

    rebound, reason = _match_live_field(
        planned_field=planned_phone,
        live_fields=ambiguous,
    )

    tests.append(
        (
            "Ambiguous live field identity blocks mutation",
            (
                rebound is None
                and "not unique"
                in reason.lower()
            ),
        )
    )

    source_text = open(
        __import__(
            "src.browser.safe_form_filler",
            fromlist=["dummy"],
        ).__file__,
        "r",
        encoding="utf-8",
    ).read()

    loop_start = source_text.find(
        "for task in tasks:"
    )

    rebind_call = source_text.find(
        "_rebind_live_field(",
        loop_start,
    )

    tests.append(
        (
            "Every real mutation loop rebinds the live field first",
            (
                loop_start >= 0
                and rebind_call > loop_start
            ),
        )
    )

    tests.append(
        (
            "Observable state ignores blank helper-control churn",
            (
                _observable_field_state(
                    {
                        "values": [
                            "",
                            "",
                        ],
                        "checked_states": [
                            False,
                            False,
                        ],
                    }
                )
                == _observable_field_state(
                    {
                        "values": [
                            "",
                        ],
                        "checked_states": [
                            False,
                        ],
                    }
                )
            ),
        )
    )

    tests.append(
        (
            "Observable state detects unexpected populated assistance value",
            (
                _observable_field_state(
                    {
                        "values": [
                            "https://example.com/portfolio",
                        ],
                        "checked_states": [
                            False,
                        ],
                    }
                )
                != _observable_field_state(
                    {
                        "values": [
                            "",
                        ],
                        "checked_states": [
                            False,
                        ],
                    }
                )
            ),
        )
    )

    source_text = open(
        __import__(
            "src.browser.safe_form_filler",
            fromlist=["dummy"],
        ).__file__,
        "r",
        encoding="utf-8",
    ).read()

    tests.append(
        (
            "Successful mutations trigger non-ready contamination check",
            (
                "_detect_nonready_mutation("
                in source_text
                and "if contamination:"
                in source_text
                and "break"
                in source_text
            ),
        )
    )

    source_text = open(
        __import__(
            "src.browser.safe_form_filler",
            fromlist=["dummy"],
        ).__file__,
        "r",
        encoding="utf-8",
    ).read().lower()

    challenge_call = source_text.find(
        "challenge = detect_page_challenge("
    )

    first_form_inspection = source_text.find(
        "frame, logical_fields = _best_frame("
    )

    tests.append(
        (
            "Page challenge detection runs before form inspection/mutation",
            (
                challenge_call >= 0
                and first_form_inspection >= 0
                and challenge_call < first_form_inspection
            ),
        )
    )

    tests.append(
        (
            "Challenge path returns zero mutations",
            (
                '"tasks_attempted": 0'
                in source_text
                and '"filled": 0'
                in source_text
                and '"mutation_blocked_by_challenge": true'
                in source_text
            ),
        )
    )

    tests.append(
        (
            "Known CAPTCHA providers are detected",
            (
                "recaptcha"
                in source_text
                and "hcaptcha"
                in source_text
                and "turnstile"
                in source_text
            ),
        )
    )

    tests.append(
        (
            "Challenge detector contains no CAPTCHA solving/bypass behavior",
            (
                "solve captcha"
                not in source_text
                and "bypass captcha"
                not in source_text
                and "captcha.solve"
                not in source_text
            ),
        )
    )

    guard_text = (
        SUBMIT_GUARD_SCRIPT
        .lower()
    )

    tests.append(
        (
            "Hard submit guard blocks submit and requestSubmit",
            (
                "prototype.submit"
                in guard_text
                and "requestsubmit"
                in guard_text
                and "preventdefault"
                in guard_text
            ),
        )
    )

    print()
    print("=" * 90)
    print(
        "SAFE DRY-RUN AUTOFILL V1.5 TEST"
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
        "✅ SAFE DRY-RUN AUTOFILL V1.5 TEST PASSED"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
