import argparse
import json
from pathlib import Path

from src.profile.applicant_profile import (
    ApplicantProfile,
    ApplicantProfileError,
)
from src.profile.value_resolver import (
    resolve_application,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Resolve safe applicant values for a previously "
            "inspected application form. This script does NOT "
            "open or modify a browser."
        )
    )

    parser.add_argument(
        "inspection_json",
        help="JSON produced by inspect_application_form.py",
    )

    parser.add_argument(
        "--profile",
        default="config/applicant_profile.json",
        help=(
            "Private applicant profile JSON "
            "(default: config/applicant_profile.json)"
        ),
    )

    parser.add_argument(
        "--resume",
        help=(
            "Path to the resume selected for this job."
        ),
    )

    parser.add_argument(
        "--json",
        dest="output_json",
        help=(
            "Optional redacted resolver-plan JSON output."
        ),
    )

    parser.add_argument(
        "--show-values",
        action="store_true",
        help=(
            "Show resolved values in terminal output. "
            "By default values are redacted/hidden."
        ),
    )

    return parser.parse_args()


def load_inspection(
    path: str | Path,
) -> dict:
    source = Path(
        path
    )

    if not source.exists():
        raise FileNotFoundError(
            f"Inspection JSON not found: {source}"
        )

    raw = json.loads(
        source.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            "Inspection JSON must be an object."
        )

    return raw


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

    inspection = load_inspection(
        args.inspection_json
    )

    plan = resolve_application(
        inspection=inspection,
        profile=profile,
        resume_path=args.resume,
    )

    print()
    print("=" * 100)
    print(
        "APPLICANT PROFILE + SAFE VALUE RESOLVER V1"
    )
    print("=" * 100)
    print()
    print(
        "Browser opened:       NO"
    )
    print(
        "Browser modified:     NO"
    )
    print(
        "Files uploaded:       NO"
    )
    print(
        "Submit attempted:     NO"
    )
    print()

    for index, field in enumerate(
        plan[
            "fields"
        ],
        start=1,
    ):
        print(
            "-" * 100
        )
        print(
            f"{index:02}. "
            f"{field.label}"
        )
        print(
            f"    Category:   "
            f"{field.category}"
        )
        print(
            f"    Required:   "
            f"{'YES' if field.required else 'NO'}"
        )
        print(
            f"    Status:     "
            f"{field.status}"
        )
        print(
            f"    Source:     "
            f"{field.source}"
        )

        if field.answer_key:
            print(
                f"    Answer key: "
                f"{field.answer_key}"
            )

        if args.show_values:
            print(
                f"    Value:      "
                f"{field.value!r}"
            )
        else:
            print(
                f"    Value:      "
                f"{'<present>' if field.value not in (None, '') else '<not resolved>'}"
            )

        print(
            f"    Reason:     "
            f"{field.reason}"
        )

    summary = plan[
        "summary"
    ]

    print()
    print("=" * 100)
    print(
        "RESOLUTION SUMMARY"
    )
    print("=" * 100)
    print(
        f"Total fields:          "
        f"{summary['total_fields']}"
    )
    print(
        f"Ready fields:          "
        f"{summary['ready_fields']}"
    )
    print(
        f"Required unresolved:   "
        f"{summary['required_unresolved']}"
    )
    print(
        f"Optional unresolved:   "
        f"{summary['optional_unresolved']}"
    )
    print(
        f"Policy mismatches:     "
        f"{summary['policy_mismatches']}"
    )
    print(
        f"Missing resume:        "
        f"{summary['missing_resume']}"
    )
    print(
        f"Ready for submission:  "
        f"{'YES' if summary['ready_for_submission'] else 'NO'}"
    )
    print(
        "Browser modified:     NO"
    )
    print(
        "Submit attempted:     NO"
    )

    if args.output_json:
        destination = Path(
            args.output_json
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        public_plan = {
            "requested_url": plan.get(
                "requested_url"
            ),
            "page_title": plan.get(
                "page_title"
            ),
            "fields": [
                field.public_dict(
                    include_values=False
                )
                for field in plan[
                    "fields"
                ]
            ],
            "summary": summary,
        }

        destination.write_text(
            json.dumps(
                public_plan,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print(
            f"Redacted JSON report:  "
            f"{destination}"
        )

    print("=" * 100)


if __name__ == "__main__":
    main()
