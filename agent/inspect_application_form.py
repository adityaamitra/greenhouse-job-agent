import argparse
import json
from pathlib import Path

from src.browser.browser_agent import inspect_application
from src.browser.field_classifier import (
    ACTION_FIXED_ANSWER,
    ACTION_IGNORE,
    ACTION_NEEDS_ASSISTANCE,
    ACTION_PROFILE_VALUE,
    ACTION_RESUME_FILE,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Inspect and classify an application form "
            "without filling or submitting it."
        )
    )

    parser.add_argument("url")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--screenshot")
    parser.add_argument("--json", dest="json_path")
    parser.add_argument(
        "--debug-context",
        action="store_true",
        help=(
            "Print local DOM context for unknown/unlabeled "
            "fields to help tune extraction."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print()
    print("=" * 100)
    print(
        "BROWSER APPLICATION AGENT V1.5 — "
        "READ-ONLY FORM INSPECTOR"
    )
    print("=" * 100)
    print()
    print("Safety mode: INSPECT ONLY")
    print("Fields will NOT be filled.")
    print("Files will NOT be uploaded.")
    print("Submit will NOT be clicked.")
    print()

    result = inspect_application(
        url=args.url,
        headless=not args.headed,
        screenshot_path=args.screenshot,
    )

    print(f"Page title:     {result['page_title'] or '-'}")
    print(f"Requested URL:  {result['requested_url']}")
    print(f"Final URL:      {result['final_url']}")
    print(f"Form frame URL: {result['form_frame_url'] or '-'}")
    print()
    print(
        f"Logical fields discovered: "
        f"{len(result['fields'])}"
    )
    print()

    counts = {
        ACTION_PROFILE_VALUE: 0,
        ACTION_FIXED_ANSWER: 0,
        ACTION_RESUME_FILE: 0,
        ACTION_NEEDS_ASSISTANCE: 0,
        ACTION_IGNORE: 0,
    }

    for index, field in enumerate(
        result["fields"],
        start=1,
    ):
        decision = field["decision"]
        action = decision["action"]

        if action in counts:
            counts[action] += 1

        print("-" * 100)
        print(
            f"{index:02}. "
            f"{field.get('label') or '[unlabeled field]'}"
        )
        print(
            f"    DOM:        "
            f"{field.get('tag')}/"
            f"{field.get('type')}"
        )
        print(
            f"    Sources:    "
            f"{field.get('source_count', 1)} control(s) "
            f"[{', '.join(field.get('source_types') or [])}]"
        )
        print(
            f"    Required:   "
            f"{'YES' if field.get('required') else 'NO'}"
        )
        print(
            f"    Category:   "
            f"{decision['category']}"
        )
        print(
            f"    Action:     "
            f"{action}"
        )

        if decision.get("answer_key"):
            print(
                f"    Answer key: "
                f"{decision['answer_key']}"
            )

        if decision.get("fixed_answer") is not None:
            print(
                f"    Policy:     "
                f"{decision['fixed_answer']}"
            )

        print(
            f"    Reason:     "
            f"{decision['reason']}"
        )

        if (
            args.debug_context
            and (
                not field.get("label")
                or decision["category"]
                == "UNKNOWN_CUSTOM_FIELD"
            )
        ):
            context = (
                field.get("context_text")
                or ""
            )

            print(
                f"    Context:    "
                f"{context[:500] or '-'}"
            )

    print()
    print("=" * 100)
    print("INSPECTION SUMMARY")
    print("=" * 100)
    print(
        f"Profile-value fields: "
        f"{counts[ACTION_PROFILE_VALUE]}"
    )
    print(
        f"Fixed-policy fields:  "
        f"{counts[ACTION_FIXED_ANSWER]}"
    )
    print(
        f"Resume fields:        "
        f"{counts[ACTION_RESUME_FILE]}"
    )
    print(
        f"Needs Assistance:     "
        f"{counts[ACTION_NEEDS_ASSISTANCE]}"
    )
    print(
        f"Ignored technical:    "
        f"{counts[ACTION_IGNORE]}"
    )
    print("Submit attempted:     NO")

    if args.screenshot:
        print(
            f"Screenshot:           "
            f"{args.screenshot}"
        )

    if args.json_path:
        destination = Path(
            args.json_path
        )
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        destination.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(
            f"JSON report:          "
            f"{args.json_path}"
        )

    print("=" * 100)


if __name__ == "__main__":
    main()
