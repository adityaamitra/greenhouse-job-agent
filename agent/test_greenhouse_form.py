from src.browser.greenhouse_form import group_fields


def field(
    index,
    *,
    label,
    field_type="text",
    name="",
    context_text="",
    required=True,
):
    return {
        "index": index,
        "tag": (
            "textarea"
            if field_type == "textarea"
            else "input"
        ),
        "type": field_type,
        "id": "",
        "name": name,
        "label": label,
        "option_label": "",
        "placeholder": "",
        "context_text": context_text,
        "required": required,
        "value": "",
        "options": [],
    }


def main():
    tests = []

    grouped = group_fields(
        [
            field(i, label="First Name*")
            for i in range(4)
        ]
    )
    tests.append(
        (
            "Duplicate First Name controls collapse",
            len(grouped) == 1
            and grouped[0]["source_count"] == 4,
        )
    )

    grouped = group_fields(
        [
            field(1, label="Phone", field_type="text"),
            field(2, label="Phone", field_type="search"),
            field(3, label="Phone", field_type="tel"),
        ]
    )
    tests.append(
        (
            "Phone widget collapses to one tel field",
            len(grouped) == 1
            and grouped[0]["type"] == "tel"
            and grouped[0]["source_count"] == 3,
        )
    )

    grouped = group_fields(
        [
            field(
                1,
                label="Attach",
                field_type="file",
                context_text="Resume/CV Attach",
            ),
            field(
                2,
                label="Attach",
                field_type="file",
                context_text="Cover Letter Attach",
            ),
        ]
    )
    tests.append(
        (
            "Same-label resume and cover letter stay separate",
            len(grouped) == 2,
        )
    )

    grouped = group_fields(
        [
            field(
                1,
                label=(
                    "Are you currently eligible to work "
                    "legally in the United States?"
                ),
                context_text=(
                    "Are you currently eligible to work "
                    "legally in the United States? Yes No"
                ),
            ),
            field(
                2,
                label="",
                context_text=(
                    "Are you currently eligible to work "
                    "legally in the United States? Yes No"
                ),
            ),
        ]
    )
    tests.append(
        (
            "Unlabeled helper merges into preceding question",
            len(grouped) == 1
            and grouped[0]["source_count"] == 2,
        )
    )

    grouped = group_fields(
        [
            field(
                1,
                label="g-recaptcha-response",
                field_type="textarea",
                name="g-recaptcha-response",
            )
        ]
    )
    tests.append(
        (
            "reCAPTCHA is removed",
            len(grouped) == 0,
        )
    )

    print()
    print("=" * 90)
    print("GREENHOUSE FORM NORMALIZATION V1.5 TEST")
    print("=" * 90)
    print()

    passed = 0

    for index, (name, ok) in enumerate(
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

    failed = len(tests) - passed

    print()
    print("=" * 90)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print()

    if failed:
        raise SystemExit(1)

    print(
        "✅ GREENHOUSE FORM NORMALIZATION "
        "V1.5 TEST PASSED"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
