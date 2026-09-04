from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
APP = (ROOT / "src" / "App.jsx").read_text(
    encoding="utf-8"
)
CSS = (ROOT / "src" / "index.css").read_text(
    encoding="utf-8"
)


def contains_all(text, values):
    return all(
        value in text
        for value in values
    )


tests = []

tests.append(
    (
        "Dashboard queries assistance_requests",
        '.from("assistance_requests")' in APP,
    )
)

tests.append(
    (
        "Browser query is limited to unresolved BROWSER rows",
        contains_all(
            APP,
            [
                '.eq("source", "BROWSER")',
                '.eq("resolved", false)',
            ],
        ),
    )
)

tests.append(
    (
        "Latest browser request is merged into application",
        "browser_assistance:" in APP
        and "latestBrowserAssistanceByApplication" in APP,
    )
)

tests.append(
    (
        "Legacy eligibility assistance message is preserved",
        "application.assistance_reason" in APP
        and "!browserHandoff" in APP,
    )
)

tests.append(
    (
        "Structured browser handoff component exists",
        "function BrowserAssistanceHandoff" in APP,
    )
)

tests.append(
    (
        "CAPTCHA / ready / review badges are rendered",
        contains_all(
            APP,
            [
                "CAPTCHA",
                "{readyCount} ready",
                "{requiredHumanCount} need review",
            ],
        ),
    )
)

tests.append(
    (
        "Selected resume is shown",
        "Selected resume" in APP,
    )
)

tests.append(
    (
        "Human-review required and optional states are distinct",
        contains_all(
            APP,
            [
                '"handoff-field-badge required"',
                '"handoff-field-badge optional"',
            ],
        ),
    )
)

tests.append(
    (
        "Only approved policy keys can expose display answers",
        "BROWSER_POLICY_ANSWER_KEYS" in APP
        and "safePolicyDisplayAnswer" in APP,
    )
)

# The raw property may appear in the redaction helper, but it must not be
# rendered directly as JSX.
direct_render = re.search(
    r"\{\s*item\.display_answer\s*\}",
    APP,
)
tests.append(
    (
        "Profile display_answer is never directly rendered",
        direct_render is None,
    )
)

tests.append(
    (
        "Historical route mismatch is surfaced",
        "Route mismatch" in APP
        and 'application.evaluation.route !==' in APP,
    )
)

tests.append(
    (
        "Browser handoff responsive CSS exists",
        contains_all(
            CSS,
            [
                ".browser-handoff",
                ".handoff-detail-grid",
                ".handoff-item-list",
                "@media (max-width: 900px)",
            ],
        ),
    )
)

print()
print("=" * 92)
print("DASHBOARD ASSISTANCE HANDOFF V1 TEST")
print("=" * 92)
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
print("=" * 92)
print(f"Passed: {passed}/{len(tests)}")
print(f"Failed: {failed}/{len(tests)}")
print()

if failed:
    raise SystemExit(1)

print(
    "✅ DASHBOARD ASSISTANCE HANDOFF V1 TEST PASSED"
)
print("=" * 92)
