from pathlib import Path


ROOT = Path(__file__).resolve().parent
APP = (
    ROOT
    / "src"
    / "App.jsx"
).read_text(
    encoding="utf-8"
)
CSS = (
    ROOT
    / "src"
    / "index.css"
).read_text(
    encoding="utf-8"
)


def contains_all(
    text,
    values,
):
    return all(
        value in text
        for value in values
    )


def balanced(
    text,
    left,
    right,
):
    count = 0

    for character in text:
        if character == left:
            count += 1
        elif character == right:
            count -= 1

        if count < 0:
            return False

    return count == 0


tests = []

tests.append(
    (
        "Dashboard queries browser_queue_runs",
        '.from("browser_queue_runs")'
        in APP,
    )
)

tests.append(
    (
        "Dashboard requests sanitized operational fields only",
        contains_all(
            APP,
            [
                "selected_count",
                "completed_count",
                "challenge_count",
                "needs_assistance_count",
                "ready_no_submit_count",
                "blocked_count",
                "error_count",
                "total_seconds",
                "submitted_count",
            ],
        ),
    )
)

tests.append(
    (
        "Browser Runs navigation tab exists",
        'label="Browser Runs"'
        in APP
        and 'activeTab === "browser"'
        in APP,
    )
)

tests.append(
    (
        "Latest Browser Queue Run summary exists",
        contains_all(
            APP,
            [
                "Latest Browser Queue Run",
                "CAPTCHA",
                "Needs Assistance",
                "Ready / No Submit",
                "Blocked + Errors",
            ],
        ),
    )
)

tests.append(
    (
        "Recent Browser Queue history table exists",
        contains_all(
            APP,
            [
                "Recent Queue History",
                "browser-runs-table",
                "BrowserRunHealthBadge",
            ],
        ),
    )
)

tests.append(
    (
        "Submission zero is visible in dashboard",
        contains_all(
            APP,
            [
                "Submissions:",
                "submitted_count",
                "browser-submit-badge",
            ],
        ),
    )
)

tests.append(
    (
        "Dashboard does not query browser history results JSON",
        "results," not in APP
        and "results\n" not in APP,
    )
)

tests.append(
    (
        "Dashboard never renders applicant profile fields in Browser Runs",
        not contains_all(
            APP,
            [
                "browser_queue_runs",
                "first_name",
                "email",
                "phone",
            ],
        ),
    )
)

tests.append(
    (
        "Browser history CSS exists",
        contains_all(
            CSS,
            [
                ".browser-run-hero",
                ".browser-run-health",
                ".browser-runs-table",
                ".browser-submit-badge",
            ],
        ),
    )
)

tests.append(
    (
        "App JSX delimiters remain balanced",
        (
            balanced(
                APP,
                "{",
                "}",
            )
            and balanced(
                APP,
                "(",
                ")",
            )
            and balanced(
                APP,
                "[",
                "]",
            )
        ),
    )
)

tests.append(
    (
        "CSS braces remain balanced",
        balanced(
            CSS,
            "{",
            "}",
        ),
    )
)

print()
print("=" * 96)
print(
    "BROWSER QUEUE HISTORY DASHBOARD V1 TEST"
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
    "✅ BROWSER QUEUE HISTORY DASHBOARD V1 TEST PASSED"
)
print("=" * 96)
