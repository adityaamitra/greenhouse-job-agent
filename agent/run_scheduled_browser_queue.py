import argparse

from src.browser.scheduled_runner import (
    MODE_BROWSER_DRY_RUN,
    MODE_BROWSER_PERSISTED,
    MODE_PREVIEW,
    SchedulerConfig,
    SchedulerConfigError,
    SchedulerLockHeld,
    run_scheduled_browser_queue,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run one Scheduled Browser Queue V1 iteration. "
            "No application submission path exists."
        )
    )
    parser.add_argument(
        "--config",
        default="config/browser_scheduler.json",
    )
    parser.add_argument(
        "--allow-persisted-mode",
        action="store_true",
        help=(
            "Required in addition to config mode "
            "BROWSER_PERSISTED."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        config = SchedulerConfig.load(
            args.config
        )
    except SchedulerConfigError as exc:
        print(
            f"SCHEDULER CONFIG ERROR: {exc}"
        )
        raise SystemExit(3)

    print()
    print("=" * 104)
    print(
        "SCHEDULED BROWSER QUEUE EXECUTION V1"
    )
    print("=" * 104)
    print(
        f"Mode:                    {config.mode}"
    )
    print(
        f"Per-run cap:             {config.limit}"
    )
    print(
        "Application statuses:    PENDING only"
    )
    print(
        "IN_PROGRESS retries:     DISABLED"
    )
    print(
        "Browser mode:            HEADLESS"
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

    if config.mode == MODE_PREVIEW:
        print(
            "Browser execution:       DISABLED"
        )
        print(
            "Supabase persistence:    DISABLED"
        )
    elif config.mode == MODE_BROWSER_DRY_RUN:
        print(
            "Browser execution:       ENABLED"
        )
        print(
            "Supabase persistence:    DISABLED"
        )
    elif config.mode == MODE_BROWSER_PERSISTED:
        print(
            "Browser execution:       ENABLED"
        )
        print(
            "Supabase persistence:    ENABLED"
        )
        print(
            "Persisted-mode allow:    "
            f"{'YES' if args.allow_persisted_mode else 'NO'}"
        )

    print("=" * 104)

    try:
        report = run_scheduled_browser_queue(
            config=config,
            allow_persisted_mode=(
                args.allow_persisted_mode
            ),
        )
    except SchedulerLockHeld as exc:
        print(
            f"SCHEDULER SKIPPED: {exc}"
        )
        raise SystemExit(10)
    except (
        SchedulerConfigError,
        RuntimeError,
    ) as exc:
        print(
            f"SCHEDULER BLOCKED: {exc}"
        )
        raise SystemExit(11)

    print()
    print("=" * 104)
    print(
        "SCHEDULED RUN RESULT"
    )
    print("=" * 104)
    print(
        f"Selected:                "
        f"{report.get('selected_count', 0)}"
    )
    print(
        f"Browser opened:          "
        f"{'YES' if report.get('browser_opened') else 'NO'}"
    )
    print(
        "Queue history persisted: "
        f"{'YES' if report.get('supabase_queue_history_persisted') else 'NO'}"
    )
    print(
        "Application submitted:   NO"
    )
    print(
        f"Scheduler report:        "
        f"{report.get('report_path', '-')}"
    )
    print("=" * 104)


if __name__ == "__main__":
    main()
