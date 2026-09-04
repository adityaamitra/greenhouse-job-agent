import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import sys
import types


# Stub scheduled browser module.
scheduled_mod = types.ModuleType(
    "src.browser.scheduled_runner"
)

scheduled_mod.MODE_BROWSER_DRY_RUN = (
    "BROWSER_DRY_RUN"
)
scheduled_mod.MODE_BROWSER_PERSISTED = (
    "BROWSER_PERSISTED"
)


class StubSchedulerConfig:
    @classmethod
    def from_dict(
        cls,
        raw,
    ):
        return dict(
            raw
        )


scheduled_mod.SchedulerConfig = (
    StubSchedulerConfig
)
scheduled_mod.run_scheduled_browser_queue = (
    lambda **kwargs: {}
)

sys.modules[
    "src.browser.scheduled_runner"
] = scheduled_mod


# Stub queue preview.
queue_mod = types.ModuleType(
    "src.browser.queue_runner"
)
queue_mod.preview_browser_queue = (
    lambda **kwargs: []
)
sys.modules[
    "src.browser.queue_runner"
] = queue_mod


# Stub repository.
repo_mod = types.ModuleType(
    "src.database.repository"
)


class StubRepository:
    pass


repo_mod.JobRepository = (
    StubRepository
)
sys.modules[
    "src.database.repository"
] = repo_mod


from src.pipeline.daily_orchestrator import (  # noqa: E402
    DAILY_MAX_BROWSER_LIMIT,
    MODE_SCAN_ONLY,
    MODE_SCAN_THEN_BROWSER_DRY_RUN,
    MODE_SCAN_THEN_BROWSER_PERSISTED,
    DailyPipelineBlocked,
    DailyPipelineConfig,
    DailyPipelineConfigError,
    assert_fresh_browser_candidates,
    run_daily_pipeline,
)

from generate_macos_daily_pipeline_scheduler import (  # noqa: E402
    build_plist,
)


def iso(
    dt,
):
    return (
        dt
        .astimezone(
            timezone.utc
        )
        .isoformat()
    )


def main():
    tests = []

    default_config = (
        DailyPipelineConfig.from_dict(
            {}
        )
    )

    tests.append(
        (
            "Default mode is SCAN_ONLY with browser cap 1",
            (
                default_config.mode
                == MODE_SCAN_ONLY
                and default_config.browser_limit
                == 1
            ),
        )
    )

    limit_blocked = False

    try:
        DailyPipelineConfig.from_dict(
            {
                "browser_limit": (
                    DAILY_MAX_BROWSER_LIMIT
                    + 1
                )
            }
        )
    except DailyPipelineConfigError:
        limit_blocked = True

    tests.append(
        (
            "Daily browser cap cannot exceed 3",
            limit_blocked,
        )
    )

    bad_mode_blocked = False

    try:
        DailyPipelineConfig.from_dict(
            {
                "mode": "UNSAFE",
            }
        )
    except DailyPipelineConfigError:
        bad_mode_blocked = True

    tests.append(
        (
            "Unknown pipeline mode fails closed",
            bad_mode_blocked,
        )
    )

    fresh_scan = {
        "board_token": "multi",
        "started_at": (
            "2026-09-04T20:00:00+00:00"
        ),
        "completed_at": (
            "2026-09-04T20:01:00+00:00"
        ),
        "jobs_discovered": 100,
        "target_role_jobs": 20,
        "us_compatible_jobs": 15,
        "jobs_eligible": 10,
        "manual_priority_count": 2,
        "agent_apply_count": 8,
        "experience_rejected_count": 3,
        "unknown_location_count": 1,
        "total_seconds": 60,
    }

    with tempfile.TemporaryDirectory() as raw:
        root = Path(
            raw
        )

        scan_only = (
            DailyPipelineConfig.from_dict(
                {
                    "mode": (
                        MODE_SCAN_ONLY
                    ),
                    "pipeline_artifacts_dir": str(
                        root
                        / "pipeline-scan"
                    ),
                    "post_scan_delay_seconds": 0,
                }
            )
        )

        browser_calls = []

        report = run_daily_pipeline(
            config=scan_only,
            agent_dir=root,
            repository=object(),
            scan_runner=lambda **kwargs: {
                "return_code": 0,
                "total_seconds": 60,
            },
            scan_lookup=lambda **kwargs: dict(
                fresh_scan
            ),
            preview_fn=lambda **kwargs: [],
            scheduled_browser_fn=lambda **kwargs: (
                browser_calls.append(
                    kwargs
                )
                or {}
            ),
        )

        tests.append(
            (
                "SCAN_ONLY completes without browser execution",
                (
                    report[
                        "status"
                    ]
                    == "COMPLETED_SCAN_ONLY"
                    and report[
                        "browser_opened"
                    ]
                    is False
                    and not browser_calls
                ),
            )
        )

        scan_fail_blocked = False

        try:
            run_daily_pipeline(
                config=scan_only,
                agent_dir=root,
                repository=object(),
                scan_runner=lambda **kwargs: {
                    "return_code": 1,
                    "total_seconds": 1,
                },
                scan_lookup=lambda **kwargs: dict(
                    fresh_scan
                ),
            )
        except DailyPipelineBlocked:
            scan_fail_blocked = True

        tests.append(
            (
                "Non-zero scanner exit blocks browser stage",
                scan_fail_blocked,
            )
        )

        missing_run_blocked = False

        try:
            run_daily_pipeline(
                config=scan_only,
                agent_dir=root,
                repository=object(),
                scan_runner=lambda **kwargs: {
                    "return_code": 0,
                    "total_seconds": 1,
                },
                scan_lookup=lambda **kwargs: None,
            )
        except DailyPipelineBlocked:
            missing_run_blocked = True

        tests.append(
            (
                "Missing fresh completed agent run fails closed",
                missing_run_blocked,
            )
        )

        zero_scan = dict(
            fresh_scan
        )
        zero_scan[
            "jobs_discovered"
        ] = 0

        zero_blocked = False

        try:
            run_daily_pipeline(
                config=scan_only,
                agent_dir=root,
                repository=object(),
                scan_runner=lambda **kwargs: {
                    "return_code": 0,
                    "total_seconds": 1,
                },
                scan_lookup=lambda **kwargs: (
                    zero_scan
                ),
            )
        except DailyPipelineBlocked:
            zero_blocked = True

        tests.append(
            (
                "Zero-job scan blocks browser stage",
                zero_blocked,
            )
        )

        dry_config = (
            DailyPipelineConfig.from_dict(
                {
                    "mode": (
                        MODE_SCAN_THEN_BROWSER_DRY_RUN
                    ),
                    "browser_limit": 1,
                    "pipeline_artifacts_dir": str(
                        root
                        / "pipeline-dry"
                    ),
                    "post_scan_delay_seconds": 0,
                }
            )
        )

        now = datetime.now(
            timezone.utc
        )

        fresh_candidate = {
            "board_token": "stripe",
            "greenhouse_job_id": "123",
            "company": "Stripe",
            "title": "Backend Engineer",
            "route": "AGENT_APPLY",
            "application_status": "PENDING",
            "score": 70,
            "confidence": 80,
            "selected_resume_file": (
                "private_resume.pdf"
            ),
            "evaluation_completed_at": iso(
                now
                + timedelta(
                    minutes=1
                )
            ),
        }

        dry_browser_calls = []

        dry_report = run_daily_pipeline(
            config=dry_config,
            agent_dir=root,
            repository=object(),
            scan_runner=lambda **kwargs: {
                "return_code": 0,
                "total_seconds": 60,
            },
            scan_lookup=lambda **kwargs: dict(
                fresh_scan
            ),
            preview_fn=lambda **kwargs: [
                dict(
                    fresh_candidate
                )
            ],
            scheduled_browser_fn=lambda **kwargs: (
                dry_browser_calls.append(
                    kwargs
                )
                or {
                    "browser_opened": True,
                    "selected_count": 1,
                    "supabase_queue_history_persisted": False,
                    "submit_clicked_by_agent": False,
                    "application_submitted": False,
                }
            ),
        )

        tests.append(
            (
                "Dry-run pipeline scans first then invokes non-persisted browser mode",
                (
                    len(
                        dry_browser_calls
                    )
                    == 1
                    and dry_browser_calls[
                        0
                    ][
                        "config"
                    ][
                        "mode"
                    ]
                    == "BROWSER_DRY_RUN"
                    and dry_browser_calls[
                        0
                    ][
                        "allow_persisted_mode"
                    ]
                    is False
                    and dry_report[
                        "browser_opened"
                    ]
                    is True
                ),
            )
        )

        tests.append(
            (
                "Pipeline report excludes selected resume filename",
                "private_resume.pdf"
                not in json.dumps(
                    dry_report
                ),
            )
        )

        stale_candidate = dict(
            fresh_candidate
        )
        stale_candidate[
            "evaluation_completed_at"
        ] = "2000-01-01T00:00:00+00:00"

        stale_blocked = False

        try:
            run_daily_pipeline(
                config=dry_config,
                agent_dir=root,
                repository=object(),
                scan_runner=lambda **kwargs: {
                    "return_code": 0,
                    "total_seconds": 60,
                },
                scan_lookup=lambda **kwargs: dict(
                    fresh_scan
                ),
                preview_fn=lambda **kwargs: [
                    stale_candidate
                ],
                scheduled_browser_fn=lambda **kwargs: {},
            )
        except DailyPipelineBlocked:
            stale_blocked = True

        tests.append(
            (
                "Stale queue candidate blocks browser execution",
                stale_blocked,
            )
        )

        no_candidate_browser_calls = []

        no_candidate_report = run_daily_pipeline(
            config=dry_config,
            agent_dir=root,
            repository=object(),
            scan_runner=lambda **kwargs: {
                "return_code": 0,
                "total_seconds": 60,
            },
            scan_lookup=lambda **kwargs: dict(
                fresh_scan
            ),
            preview_fn=lambda **kwargs: [],
            scheduled_browser_fn=lambda **kwargs: (
                no_candidate_browser_calls.append(
                    kwargs
                )
                or {}
            ),
        )

        tests.append(
            (
                "Fresh scan with no browser candidates exits cleanly",
                (
                    no_candidate_report[
                        "status"
                    ]
                    == "COMPLETED_NO_BROWSER_CANDIDATES"
                    and not no_candidate_browser_calls
                ),
            )
        )

        persisted_config = (
            DailyPipelineConfig.from_dict(
                {
                    "mode": (
                        MODE_SCAN_THEN_BROWSER_PERSISTED
                    ),
                    "pipeline_artifacts_dir": str(
                        root
                        / "pipeline-persist"
                    ),
                    "post_scan_delay_seconds": 0,
                }
            )
        )

        persist_gate_blocked = False

        try:
            run_daily_pipeline(
                config=persisted_config,
                agent_dir=root,
                repository=object(),
            )
        except DailyPipelineConfigError:
            persist_gate_blocked = True

        tests.append(
            (
                "Persisted browser stage requires explicit second gate",
                persist_gate_blocked,
            )
        )

        persist_calls = []

        persisted_report = run_daily_pipeline(
            config=persisted_config,
            allow_browser_persistence=True,
            agent_dir=root,
            repository=object(),
            scan_runner=lambda **kwargs: {
                "return_code": 0,
                "total_seconds": 60,
            },
            scan_lookup=lambda **kwargs: dict(
                fresh_scan
            ),
            preview_fn=lambda **kwargs: [
                dict(
                    fresh_candidate
                )
            ],
            scheduled_browser_fn=lambda **kwargs: (
                persist_calls.append(
                    kwargs
                )
                or {
                    "browser_opened": True,
                    "selected_count": 1,
                    "supabase_queue_history_persisted": True,
                    "submit_clicked_by_agent": False,
                    "application_submitted": False,
                }
            ),
        )

        tests.append(
            (
                "Explicit persisted pipeline passes persistence to scheduled browser stage",
                (
                    persist_calls[
                        0
                    ][
                        "config"
                    ][
                        "mode"
                    ]
                    == "BROWSER_PERSISTED"
                    and persist_calls[
                        0
                    ][
                        "allow_persisted_mode"
                    ]
                    is True
                    and persisted_report[
                        "browser_history_persisted"
                    ]
                    is True
                ),
            )
        )

        missing_history_blocked = False

        try:
            run_daily_pipeline(
                config=persisted_config,
                allow_browser_persistence=True,
                agent_dir=root,
                repository=object(),
                scan_runner=lambda **kwargs: {
                    "return_code": 0,
                    "total_seconds": 60,
                },
                scan_lookup=lambda **kwargs: dict(
                    fresh_scan
                ),
                preview_fn=lambda **kwargs: [
                    dict(
                        fresh_candidate
                    )
                ],
                scheduled_browser_fn=lambda **kwargs: {
                    "browser_opened": True,
                    "selected_count": 1,
                    "supabase_queue_history_persisted": False,
                    "submit_clicked_by_agent": False,
                    "application_submitted": False,
                },
            )
        except DailyPipelineBlocked:
            missing_history_blocked = True

        tests.append(
            (
                "Persisted pipeline fails if Browser Queue history is missing",
                missing_history_blocked,
            )
        )

        submission_blocked = False

        try:
            run_daily_pipeline(
                config=dry_config,
                agent_dir=root,
                repository=object(),
                scan_runner=lambda **kwargs: {
                    "return_code": 0,
                    "total_seconds": 60,
                },
                scan_lookup=lambda **kwargs: dict(
                    fresh_scan
                ),
                preview_fn=lambda **kwargs: [
                    dict(
                        fresh_candidate
                    )
                ],
                scheduled_browser_fn=lambda **kwargs: {
                    "browser_opened": True,
                    "selected_count": 1,
                    "supabase_queue_history_persisted": False,
                    "submit_clicked_by_agent": False,
                    "application_submitted": True,
                },
            )
        except DailyPipelineBlocked:
            submission_blocked = True

        tests.append(
            (
                "Submission invariant violation blocks daily pipeline",
                submission_blocked,
            )
        )

        plist = build_plist(
            agent_dir=root.resolve(),
            python_path="/usr/bin/python3",
            config_path=(
                "config/daily_pipeline.json"
            ),
            hour=10,
            minute=30,
            allow_browser_persistence=False,
        )

        tests.append(
            (
                "Generated daily plist does not allow browser persistence by default",
                (
                    "--allow-browser-persistence"
                    not in plist[
                        "ProgramArguments"
                    ]
                    and plist[
                        "RunAtLoad"
                    ]
                    is False
                ),
            )
        )

        persisted_plist = build_plist(
            agent_dir=root.resolve(),
            python_path="/usr/bin/python3",
            config_path=(
                "config/daily_pipeline.json"
            ),
            hour=10,
            minute=30,
            allow_browser_persistence=True,
        )

        tests.append(
            (
                "Persisted daily plist requires explicit generator opt-in",
                "--allow-browser-persistence"
                in persisted_plist[
                    "ProgramArguments"
                ],
            )
        )

    source = Path(
        __import__(
            "src.pipeline.daily_orchestrator",
            fromlist=[
                "dummy"
            ],
        ).__file__
    ).read_text(
        encoding="utf-8"
    ).lower()

    tests.append(
        (
            "Daily orchestrator contains no submit/click call path",
            (
                ".submit("
                not in source
                and "requestsubmit"
                not in source
                and ".click("
                not in source
            ),
        )
    )

    generator_source = Path(
        __import__(
            "generate_macos_daily_pipeline_scheduler"
        ).__file__
    ).read_text(
        encoding="utf-8"
    ).lower()

    tests.append(
        (
            "Daily plist generator executes no system scheduling command",
            (
                "launchctl"
                not in generator_source
                and "subprocess"
                not in generator_source
                and "os.system"
                not in generator_source
            ),
        )
    )

    tests.append(
        (
            "Daily browser preview never opts into IN_PROGRESS",
            "include_in_progress=false"
            in source.replace(
                " ",
                ""
            ),
        )
    )

    print()
    print("=" * 104)
    print(
        "DAILY PIPELINE ORCHESTRATION V1 TEST"
    )
    print("=" * 104)
    print()

    passed = 0

    for index, (
        name,
        ok,
    ) in enumerate(
        tests,
        start=1,
    ):
        print(
            f"{index:02}. "
            f"{'✅ PASS' if ok else '❌ FAIL'} — "
            f"{name}"
        )

        if ok:
            passed += 1

    failed = (
        len(
            tests
        )
        - passed
    )

    print()
    print("=" * 104)
    print(
        f"Passed: {passed}/{len(tests)}"
    )
    print(
        f"Failed: {failed}/{len(tests)}"
    )
    print()

    if failed:
        raise SystemExit(
            1
        )

    print(
        "✅ DAILY PIPELINE ORCHESTRATION V1 TEST PASSED"
    )
    print("=" * 104)


if __name__ == "__main__":
    main()
