import argparse
import plistlib
import sys
from pathlib import Path


LABEL = (
    "com.greenhouse-job-agent."
    "browser-queue"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a macOS plist for Scheduled "
            "Browser Queue Execution V1. "
            "This command only writes the plist file."
        )
    )
    parser.add_argument(
        "--agent-dir",
        required=True,
    )
    parser.add_argument(
        "--hour",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--minute",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
    )
    parser.add_argument(
        "--config",
        default="config/browser_scheduler.json",
    )
    parser.add_argument(
        "--allow-persisted-mode",
        action="store_true",
    )
    parser.add_argument(
        "--output",
        default=(
            "browser_runs/scheduler/"
            "com.greenhouse-job-agent."
            "browser-queue.plist"
        ),
    )
    return parser.parse_args()


def build_plist(
    *,
    agent_dir: Path,
    python_path: str,
    config_path: str,
    hour: int,
    minute: int,
    allow_persisted_mode: bool,
) -> dict:
    if not agent_dir.is_absolute():
        raise ValueError(
            "--agent-dir must be an absolute path."
        )

    if not (0 <= hour <= 23):
        raise ValueError(
            "--hour must be 0-23."
        )

    if not (0 <= minute <= 59):
        raise ValueError(
            "--minute must be 0-59."
        )

    scheduler_root = (
        agent_dir
        / "browser_runs"
        / "scheduler"
    )
    scheduler_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    program_arguments = [
        python_path,
        str(
            agent_dir
            / "run_scheduled_browser_queue.py"
        ),
        "--config",
        str(
            agent_dir
            / config_path
        ),
    ]

    if allow_persisted_mode:
        program_arguments.append(
            "--allow-persisted-mode"
        )

    return {
        "Label": LABEL,
        "ProgramArguments": (
            program_arguments
        ),
        "WorkingDirectory": str(
            agent_dir
        ),
        "StartCalendarInterval": {
            "Hour": hour,
            "Minute": minute,
        },
        "RunAtLoad": False,
        "StandardOutPath": str(
            scheduler_root
            / "launchd.stdout.log"
        ),
        "StandardErrorPath": str(
            scheduler_root
            / "launchd.stderr.log"
        ),
    }


def main():
    args = parse_args()
    agent_dir = Path(
        args.agent_dir
    ).expanduser().resolve()

    payload = build_plist(
        agent_dir=agent_dir,
        python_path=args.python,
        config_path=args.config,
        hour=args.hour,
        minute=args.minute,
        allow_persisted_mode=(
            args.allow_persisted_mode
        ),
    )

    output = (
        agent_dir
        / args.output
    )
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output.open("wb") as handle:
        plistlib.dump(
            payload,
            handle,
            sort_keys=False,
        )

    print(
        f"Generated: {output}"
    )
    print(
        "Generation complete; no system scheduling command was executed."
    )


if __name__ == "__main__":
    main()
