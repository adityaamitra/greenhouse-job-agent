import argparse
import json
from pathlib import Path

from src.database.repository import (
    BROWSER_ROUTE_AGENT_CONTINUE,
    BROWSER_ROUTE_NEEDS_ASSISTANCE,
    JobRepository,
    sanitize_browser_handoff,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Persist a redacted Browser Assistance Handoff "
            "into Supabase. This command does not open a browser."
        )
    )

    parser.add_argument(
        "handoff_json",
        help="Browser Assistance Handoff V1 JSON.",
    )

    identity = parser.add_mutually_exclusive_group(
        required=True
    )

    identity.add_argument(
        "--job-id",
        help="Existing internal jobs.id UUID.",
    )

    identity.add_argument(
        "--greenhouse-job-id",
        help="Greenhouse job id; requires --board-token.",
    )

    parser.add_argument(
        "--board-token",
        help="Greenhouse board token when using --greenhouse-job-id.",
    )

    return parser.parse_args()


def load_json(path):
    source = Path(
        path
    )

    if not source.is_file():
        raise FileNotFoundError(
            f"Handoff JSON not found: {source}"
        )

    payload = json.loads(
        source.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Handoff JSON must contain an object."
        )

    return payload


def main():
    args = parse_args()

    handoff = sanitize_browser_handoff(
        load_json(
            args.handoff_json
        )
    )

    repository = JobRepository()

    job_id = args.job_id

    if args.greenhouse_job_id:
        if not args.board_token:
            print(
                "ERROR: --board-token is required with "
                "--greenhouse-job-id."
            )
            raise SystemExit(
                2
            )

        job_id = repository.find_job_id(
            board_token=(
                args.board_token
            ),
            greenhouse_job_id=(
                args.greenhouse_job_id
            ),
        )

        if not job_id:
            print(
                "ERROR: matching job row was not found."
            )
            raise SystemExit(
                3
            )

    try:
        application_id = (
            repository
            .sync_browser_assistance_handoff(
                job_id=(
                    job_id
                ),
                handoff=(
                    handoff
                ),
            )
        )
    except RuntimeError as exc:
        print()
        print(
            f"ROUTING GUARD: {exc}"
        )
        print(
            "No browser assistance rows were changed."
        )
        raise SystemExit(
            4
        )

    summary = (
        handoff[
            "summary"
        ]
    )

    print()
    print("=" * 90)
    print(
        "SUPABASE BROWSER HANDOFF INTEGRATION V1.1"
    )
    print("=" * 90)
    print(
        f"Route:                 "
        f"{handoff['route']}"
    )
    print(
        f"Challenge detected:    "
        f"{'YES' if summary['challenge_detected'] else 'NO'}"
    )
    print(
        f"Deterministic ready:   "
        f"{summary['ready_count']}"
    )
    print(
        f"Required human fields: "
        f"{summary['required_human_count']}"
    )
    print(
        f"Selected resume:       "
        f"{handoff.get('selected_resume') or '-'}"
    )
    print(
        "Profile values stored:  NO"
    )
    print(
        f"Application row:       "
        f"{application_id}"
    )
    print(
        "Browser opened:         NO"
    )
    print(
        "Application submitted:  NO"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()
