import argparse
import json
from pathlib import Path

from src.browser.safe_form_filler import (
    safe_fill_application,
)
from src.profile.applicant_profile import (
    ApplicantProfile,
    ApplicantProfileError,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Fill only deterministic READY fields on a Greenhouse "
            "application while hard-blocking submission."
        )
    )

    parser.add_argument(
        "url",
        help="Greenhouse application URL.",
    )

    parser.add_argument(
        "--profile",
        default="config/applicant_profile.json",
        help="Private applicant-profile JSON.",
    )

    parser.add_argument(
        "--resume",
        required=True,
        help="Resume file selected for this job.",
    )

    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show Chromium while the safe fill runs.",
    )

    parser.add_argument(
        "--hold-seconds",
        type=int,
        default=0,
        help=(
            "Keep the filled page open for N seconds before closing. "
            "Useful with --headed."
        ),
    )

    parser.add_argument(
        "--json",
        dest="output_json",
        help="Optional redacted fill report.",
    )

    parser.add_argument(
        "--screenshot",
        help=(
            "Optional screenshot after filling. WARNING: this can "
            "contain personal information and must stay private."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    try:
        profile = ApplicantProfile.load(
            args.profile
        )
    except ApplicantProfileError as exc:
        print(
            f"PROFILE ERROR: {exc}"
        )
        raise SystemExit(
            2
        )

    result = safe_fill_application(
        url=args.url,
        profile=profile,
        resume_path=args.resume,
        headless=not args.headed,
        hold_seconds=max(
            0,
            args.hold_seconds,
        ),
        screenshot_path=args.screenshot,
    )

    print()
    print("=" * 100)
    print(
        "BROWSER APPLICATION AGENT — SAFE DRY-RUN AUTOFILL V1.5"
    )
    print("=" * 100)
    print()
    print(
        "Mode:                  FILL READY FIELDS ONLY"
    )
    print(
        "Submit button clicks:  DISABLED"
    )
    print(
        "Form submission:       HARD-BLOCKED"
    )
    print(
        "Enter key submission:  NOT USED"
    )
    print(
        "Assistance fields:     UNTOUCHED"
    )
    print()

    for index, item in enumerate(
        result[
            "fill_results"
        ],
        start=1,
    ):
        print(
            "-" * 100
        )
        print(
            f"{index:02}. "
            f"{item['label']}"
        )
        print(
            f"    Category:   "
            f"{item['category']}"
        )
        print(
            f"    Operation:  "
            f"{item['operation']}"
        )
        print(
            f"    Status:     "
            f"{item['status']}"
        )
        print(
            f"    Source:     "
            f"{item['source']}"
        )
        print(
            f"    Reason:     "
            f"{item['reason']}"
        )

    summary = result[
        "fill_summary"
    ]

    resolution = result[
        "resolution_summary"
    ]

    print()
    print("=" * 100)
    print(
        "SAFE FILL SUMMARY"
    )
    print("=" * 100)
    print(
        f"Ready tasks attempted:         "
        f"{summary['tasks_attempted']}"
    )
    print(
        f"Fields/files filled:           "
        f"{summary['filled']}"
    )
    print(
        f"Fill failures:                 "
        f"{summary['fill_failed']}"
    )
    print(
        f"Required assistance untouched: "
        f"{summary['required_assistance_untouched']}"
    )
    print(
        f"Optional unresolved untouched: "
        f"{summary['optional_unresolved_untouched']}"
    )
    print(
        f"Policy mismatches:             "
        f"{resolution['policy_mismatches']}"
    )
    print(
        f"Missing resume:                "
        f"{resolution['missing_resume']}"
    )
    print(
        f"Submit attempts blocked:       "
        f"{summary['submit_attempts_blocked']}"
    )
    print(
        "Submit clicked by agent:       NO"
    )
    print(
        "Application submitted:         NO"
    )
    print(
        f"Page challenge detected:        "
        f"{'YES' if summary['page_challenge_detected'] else 'NO'}"
    )
    print(
        f"Mutation blocked by challenge:  "
        f"{'YES' if summary['mutation_blocked_by_challenge'] else 'NO'}"
    )
    print(
        f"Non-ready mutation detected:    "
        f"{'YES' if summary['nonready_mutation_detected'] else 'NO'}"
    )
    print(
        "Non-ready verification:        AFTER EACH SUCCESSFUL MUTATION"
    )

    if summary[
        "page_challenge_detected"
    ]:
        for reason in summary[
            "page_challenge_reasons"
        ]:
            print(
                f"Challenge reason:               "
                f"{reason}"
            )

    if summary[
        "nonready_mutation_detected"
    ]:
        print(
            f"SAFETY VIOLATION:              "
            f"{summary['nonready_mutation_reason']}"
        )

    if args.screenshot:
        print(
            f"PRIVATE screenshot:             "
            f"{args.screenshot}"
        )

    if args.output_json:
        destination = Path(
            args.output_json
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
            f"Redacted JSON report:           "
            f"{destination}"
        )

    print("=" * 100)


if __name__ == "__main__":
    main()
