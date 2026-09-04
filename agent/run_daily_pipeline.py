import argparse
from pathlib import Path

from src.pipeline.daily_orchestrator import (
    MODE_SCAN_ONLY,
    MODE_SCAN_THEN_BROWSER_DRY_RUN,
    MODE_SCAN_THEN_BROWSER_PERSISTED,
    DailyPipelineBlocked,
    DailyPipelineConfig,
    DailyPipelineConfigError,
    run_daily_pipeline,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Run Greenhouse discovery/scoring first, then "
            "optionally run the safe Browser Queue. "
            "Application submission remains hard-blocked."
        )
    )

    parser.add_argument(
        "--config",
        default=(
            "config/"
            "daily_pipeline.json"
        ),
    )

    parser.add_argument(
        "--allow-browser-persistence",
        action="store_true",
        help=(
            "Required in addition to "
            "SCAN_THEN_BROWSER_PERSISTED mode."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    try:
        config = (
            DailyPipelineConfig.load(
                args.config
            )
        )
    except DailyPipelineConfigError as exc:
        print(
            f"DAILY PIPELINE CONFIG ERROR: {exc}"
        )
        raise SystemExit(
            3
        )

    print()
    print("=" * 104)
    print(
        "DAILY PIPELINE ORCHESTRATION V1"
    )
    print("=" * 104)
    print(
        f"Mode:                    {config.mode}"
    )
    print(
        "Stage 1:                 Greenhouse scan + scoring"
    )
    print(
        f"Browser cap:             {config.browser_limit}"
    )
    print(
        "Browser statuses:        PENDING only"
    )
    print(
        "Browser IN_PROGRESS:     DISABLED"
    )
    print(
        "Browser mode:            HEADLESS"
    )
    print(
        "Fresh-evaluation guard:  REQUIRED"
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

    if (
        config.mode
        == MODE_SCAN_ONLY
    ):
        print(
            "Browser execution:       DISABLED"
        )
        print(
            "Browser persistence:     DISABLED"
        )

    elif (
        config.mode
        == MODE_SCAN_THEN_BROWSER_DRY_RUN
    ):
        print(
            "Browser execution:       ENABLED"
        )
        print(
            "Browser persistence:     DISABLED"
        )

    elif (
        config.mode
        == MODE_SCAN_THEN_BROWSER_PERSISTED
    ):
        print(
            "Browser execution:       ENABLED"
        )
        print(
            "Browser persistence:     ENABLED"
        )
        print(
            "Persistence allow:       "
            f"{'YES' if args.allow_browser_persistence else 'NO'}"
        )

    print("=" * 104)

    try:
        report = run_daily_pipeline(
            config=config,
            allow_browser_persistence=(
                args.allow_browser_persistence
            ),
            agent_dir=Path.cwd(),
        )

    except (
        DailyPipelineConfigError,
        DailyPipelineBlocked,
        RuntimeError,
    ) as exc:
        print(
            f"DAILY PIPELINE BLOCKED: {exc}"
        )
        raise SystemExit(
            11
        )

    scan = (
        report.get(
            "scan"
        )
        or {}
    )

    print()
    print("=" * 104)
    print(
        "DAILY PIPELINE RESULT"
    )
    print("=" * 104)
    print(
        f"Status:                  {report.get('status')}"
    )
    print(
        f"Jobs discovered:         {scan.get('jobs_discovered', 0)}"
    )
    print(
        f"Target roles:            {scan.get('target_role_jobs', 0)}"
    )
    print(
        f"US compatible:           {scan.get('us_compatible_jobs', 0)}"
    )
    print(
        f"Eligible/scored:         {scan.get('jobs_eligible', 0)}"
    )
    print(
        f"Agent apply:             {scan.get('agent_apply_count', 0)}"
    )
    print(
        f"Browser candidates:      "
        f"{len(report.get('browser_candidates') or [])}"
    )
    print(
        f"Browser opened:          "
        f"{'YES' if report.get('browser_opened') else 'NO'}"
    )
    print(
        "Browser history:         "
        f"{'YES' if report.get('browser_history_persisted') else 'NO'}"
    )
    print(
        "Application submitted:   NO"
    )
    print(
        f"Pipeline report:         {report.get('report_path', '-')}"
    )
    print("=" * 104)


if __name__ == "__main__":
    main()
