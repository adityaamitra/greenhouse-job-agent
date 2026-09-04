import argparse

from src.browser.orchestrator import (
    orchestrate_browser_application,
)
from src.profile.applicant_profile import (
    ApplicantProfile,
    ApplicantProfileError,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run Browser Orchestrator V1 for one "
            "tracked AGENT_APPLY Greenhouse job. "
            "This command has NO submit path."
        )
    )

    parser.add_argument(
        "--board-token",
        required=True,
    )

    parser.add_argument(
        "--greenhouse-job-id",
        required=True,
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
            "browser_runs/"
            "orchestrator"
        ),
    )

    parser.add_argument(
        "--headed",
        action="store_true",
    )

    parser.add_argument(
        "--no-persist",
        action="store_true",
        help=(
            "Run the complete browser workflow "
            "without changing Supabase."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print()
    print("=" * 100)
    print(
        "BROWSER ORCHESTRATOR V1"
    )
    print("=" * 100)
    print(
        "Allowed matcher route:   AGENT_APPLY"
    )
    print(
        "ATS scope:               Greenhouse only"
    )
    print(
        "CAPTCHA bypass:          DISABLED"
    )
    print(
        "Submit clicks:           NONE"
    )
    print(
        "Application submission:  HARD-BLOCKED"
    )
    print(
        "PII artifacts:           REDACTED"
    )
    print()

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

    try:
        result = (
            orchestrate_browser_application(
                board_token=(
                    args.board_token
                ),
                greenhouse_job_id=(
                    args.greenhouse_job_id
                ),
                profile=(
                    profile
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
                    not args.no_persist
                ),
            )
        )
    except RuntimeError as exc:
        print(
            f"ORCHESTRATOR BLOCKED: {exc}"
        )
        print(
            "Application submitted:  NO"
        )
        raise SystemExit(
            4
        )

    print("=" * 100)
    print(
        "ORCHESTRATION RESULT"
    )
    print("=" * 100)
    print(
        f"Company:                "
        f"{result.get('company') or '-'}"
    )
    print(
        f"Job:                    "
        f"{result.get('job_title') or '-'}"
    )
    print(
        f"Matcher route:          "
        f"{result['matcher_route']}"
    )
    print(
        f"Selected resume:        "
        f"{result['selected_resume']}"
    )
    print(
        f"Outcome:                "
        f"{result['outcome']}"
    )
    print(
        f"Handoff route:          "
        f"{result['handoff_route']}"
    )
    print(
        f"Challenge detected:     "
        f"{'YES' if result['challenge_detected'] else 'NO'}"
    )
    print(
        f"Ready fields:           "
        f"{result['ready_count']}"
    )
    print(
        f"Required human fields:  "
        f"{result['required_human_count']}"
    )
    print(
        f"Fill tasks attempted:   "
        f"{result['fill_tasks_attempted']}"
    )
    print(
        f"Fields/files filled:    "
        f"{result['filled']}"
    )
    print(
        f"Fill failures:          "
        f"{result['fill_failed']}"
    )
    print(
        f"Browser modified:       "
        f"{'YES' if result['browser_modified'] else 'NO'}"
    )
    print(
        f"Supabase persisted:     "
        f"{'YES' if result['persisted'] else 'NO'}"
    )
    print(
        "Submit clicked by agent: NO"
    )
    print(
        "Application submitted:   NO"
    )
    print(
        f"Orchestrator report:    "
        f"{result['artifacts']['orchestrator']}"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()
