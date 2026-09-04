import argparse
import json
from pathlib import Path

from src.browser.assistance_handoff import (
    build_assistance_handoff,
    render_handoff_markdown,
)
from src.profile.applicant_profile import (
    ApplicantProfile,
    ApplicantProfileError,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a redacted Browser Assistance Handoff packet "
            "from an existing Greenhouse inspection and optional "
            "safe-fill report. This script does not open a browser."
        )
    )

    parser.add_argument(
        "inspection_json",
        help="Inspection JSON from inspect_application_form.py",
    )

    parser.add_argument(
        "--profile",
        default="config/applicant_profile.json",
        help="Private applicant profile JSON.",
    )

    parser.add_argument(
        "--resume",
        required=True,
        help="Resume selected for this job.",
    )

    parser.add_argument(
        "--fill-report",
        help=(
            "Optional JSON report from dry_run_fill_application.py. "
            "Use this to include CAPTCHA/challenge status."
        ),
    )

    parser.add_argument(
        "--company",
        help="Optional company override.",
    )

    parser.add_argument(
        "--job-title",
        help="Optional job-title override.",
    )

    parser.add_argument(
        "--json",
        dest="output_json",
        help="Optional handoff JSON output.",
    )

    parser.add_argument(
        "--markdown",
        dest="output_markdown",
        help="Optional Markdown handoff output.",
    )

    return parser.parse_args()


def load_json(path):
    source = Path(
        path
    )

    if not source.exists():
        raise FileNotFoundError(
            f"JSON file not found: {source}"
        )

    raw = json.loads(
        source.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            f"Expected JSON object: {source}"
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

    inspection = load_json(
        args.inspection_json
    )

    fill_report = None

    if args.fill_report:
        fill_report = load_json(
            args.fill_report
        )

    packet = build_assistance_handoff(
        inspection=inspection,
        profile=profile,
        resume_path=args.resume,
        fill_report=fill_report,
        company=args.company,
        job_title=args.job_title,
    )

    markdown = render_handoff_markdown(
        packet
    )

    print()
    print(markdown)

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
                packet,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print(
            f"JSON packet: {destination}"
        )

    if args.output_markdown:
        destination = Path(
            args.output_markdown
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.write_text(
            markdown,
            encoding="utf-8",
        )

        print(
            f"Markdown packet: {destination}"
        )


if __name__ == "__main__":
    main()
