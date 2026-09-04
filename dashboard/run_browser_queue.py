import argparse

from src.browser.queue_runner import (
    preview_browser_queue,
    run_browser_queue,
)
from src.database.repository import (
    JobRepository,
)
from src.profile.applicant_profile import (
    ApplicantProfile,
    ApplicantProfileError,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run Browser Queue Runner V1. "
            "It processes bounded AGENT_APPLY jobs "
            "sequentially and has NO submit path."
        )
    )

    parser.add_argument(
        "--profile",
        default=(
            "config/"
            "applicant_profile.json"
        ),
    )

    parser.add_argument(
        "--resume-dir",
        default="resumes",
    )

    parser.add_argument(
        "--artifacts-dir",
        default=(
            "browser_runs/queue"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--board-token",
        default=None,
    )

    parser.add_argument(
        "--order",
        choices=[
            "oldest",
            "newest",
            "fit",
        ],
        default="oldest",
    )

    parser.add_argument(
        "--include-in-progress",
        action="store_true",
        help=(
            "Also allow IN_PROGRESS rows. "
            "Default queue is PENDING only."
        ),
    )

    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--headed",
        action="store_true",
    )

    parser.add_argument(
        "--persist",
        action="store_true",
        help=(
            "Persist assistance/continuation state. "
            "Default is no Supabase handoff write."
        ),
    )

    parser.add_argument(
        "--list-only",
        action="store_true",
        help=(
            "Preview selected queue rows without "
            "opening any browser."
        ),
    )

    return parser.parse_args()


def print_candidate(
    index,
    row,
):
    print(
        f"{index:02}. "
        f"{row.get('company') or '-'} — "
        f"{row.get('title') or '-'}"
    )

    print(
        "    "
        f"Board: {row.get('board_token') or '-'}"
        " | "
        f"Greenhouse ID: "
        f"{row.get('greenhouse_job_id') or '-'}"
    )

    print(
        "    "
        f"Status: {row.get('application_status') or '-'}"
        " | "
        f"Fit: {row.get('score') if row.get('score') is not None else '-'}"
        " | "
        f"Confidence: "
        f"{row.get('confidence') if row.get('confidence') is not None else '-'}"
        " | "
        f"Resume: {row.get('selected_resume_file') or '-'}"
    )


def main():
    args = parse_args()

    print()
    print("=" * 104)
    print(
        "BROWSER QUEUE RUNNER V1"
    )
    print("=" * 104)
    print(
        "Queue route:              AGENT_APPLY only"
    )
    print(
        "Default statuses:         PENDING only"
    )
    print(
        "Needs Assistance rows:    SKIPPED"
    )
    print(
        "ATS scope:                Greenhouse only"
    )
    print(
        "CAPTCHA bypass:           DISABLED"
    )
    print(
        "Submit clicks:            NONE"
    )
    print(
        "Application submission:   HARD-BLOCKED"
    )
    print(
        f"Supabase persistence:     "
        f"{'ENABLED' if args.persist else 'DISABLED'}"
    )
    print(
        f"Queue limit:              {args.limit}"
    )
    print()

    repository = (
        JobRepository()
    )

    try:

        candidates = (
            preview_browser_queue(
                repository=repository,
                limit=args.limit,
                include_in_progress=(
                    args.include_in_progress
                ),
                board_token=(
                    args.board_token
                ),
                order=(
                    args.order
                ),
            )
        )

    except (
        RuntimeError,
        ValueError,
    ) as exc:

        print(
            f"QUEUE PREVIEW BLOCKED: {exc}"
        )

        raise SystemExit(
            4
        )

    if not candidates:

        print(
            "No Browser Queue candidates found."
        )
        print(
            "Application submitted:   NO"
        )
        return

    print(
        "Selected queue:"
    )
    print()

    for index, row in enumerate(
        candidates,
        start=1,
    ):

        print_candidate(
            index,
            row,
        )

    print()

    if args.list_only:

        print(
            "List-only mode: browser was not opened."
        )
        print(
            "Application submitted:   NO"
        )
        return

    try:

        profile = (
            ApplicantProfile.load(
                args.profile
            )
        )

    except ApplicantProfileError as exc:

        print(
            f"PROFILE ERROR: {exc}"
        )

        raise SystemExit(
            2
        )

    report = (
        run_browser_queue(
            profile=profile,
            repository=repository,
            limit=args.limit,
            include_in_progress=(
                args.include_in_progress
            ),
            board_token=(
                args.board_token
            ),
            order=(
                args.order
            ),
            resume_dir=(
                args.resume_dir
            ),
            artifacts_dir=(
                args.artifacts_dir
            ),
            headless=(
                not args.headed
            ),
            persist=(
                args.persist
            ),
            delay_seconds=(
                args.delay_seconds
            ),
        )
    )

    print()
    print("=" * 104)
    print(
        "QUEUE RESULT"
    )
    print("=" * 104)

    for index, row in enumerate(
        report[
            "results"
        ],
        start=1,
    ):

        print(
            f"{index:02}. "
            f"{row.get('company') or '-'} — "
            f"{row.get('title') or '-'}"
        )

        print(
            "    "
            f"Queue status: {row['queue_status']}"
            " | "
            f"Outcome: {row.get('outcome') or '-'}"
            " | "
            f"Challenge: "
            f"{'YES' if row['challenge_detected'] else 'NO'}"
        )

        if row.get(
            "error"
        ):

            print(
                "    "
                f"{row['error_type']}: "
                f"{row['error']}"
            )

    summary = (
        report[
            "summary"
        ]
    )

    print()
    print(
        f"Selected:                {summary['selected']}"
    )
    print(
        f"Completed:               {summary['completed']}"
    )
    print(
        f"Needs Assistance:        {summary['needs_assistance']}"
    )
    print(
        f"Ready / no submit:       {summary['ready_no_submit']}"
    )
    print(
        f"Blocked:                 {summary['blocked']}"
    )
    print(
        f"Errors:                  {summary['errors']}"
    )
    print(
        f"Application submitted:   NO"
    )
    print(
        f"Queue report:            {report['report_path']}"
    )
    print("=" * 104)


if __name__ == "__main__":
    main()
