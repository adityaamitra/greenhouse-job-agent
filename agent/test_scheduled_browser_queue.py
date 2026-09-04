import json
from pathlib import Path
import tempfile
import sys
import types


queue_mod = types.ModuleType(
    "src.browser.queue_runner"
)
queue_mod.preview_browser_queue = (
    lambda **kwargs: []
)
queue_mod.run_browser_queue = (
    lambda **kwargs: {}
)
sys.modules[
    "src.browser.queue_runner"
] = queue_mod

repo_mod = types.ModuleType(
    "src.database.repository"
)


class StubRepository:
    pass


repo_mod.JobRepository = StubRepository
sys.modules[
    "src.database.repository"
] = repo_mod

profile_mod = types.ModuleType(
    "src.profile.applicant_profile"
)


class StubProfile:
    @staticmethod
    def load(_path):
        return object()


profile_mod.ApplicantProfile = StubProfile
sys.modules[
    "src.profile.applicant_profile"
] = profile_mod


from src.browser.scheduled_runner import (  # noqa: E402
    MODE_BROWSER_DRY_RUN,
    MODE_BROWSER_PERSISTED,
    MODE_PREVIEW,
    SCHEDULED_MAX_LIMIT,
    SchedulerConfig,
    SchedulerConfigError,
    SchedulerLockHeld,
    SingleRunLock,
    run_scheduled_browser_queue,
)
from generate_macos_browser_scheduler import (  # noqa: E402
    build_plist,
)


def main():
    tests = []

    config = SchedulerConfig.from_dict(
        {}
    )

    tests.append(
        (
            "Default scheduler mode is PREVIEW",
            (
                config.mode == MODE_PREVIEW
                and config.limit == 1
            ),
        )
    )

    limit_blocked = False
    try:
        SchedulerConfig.from_dict(
            {
                "limit": (
                    SCHEDULED_MAX_LIMIT + 1
                )
            }
        )
    except SchedulerConfigError:
        limit_blocked = True

    tests.append(
        (
            "Scheduled per-run cap cannot exceed 3",
            limit_blocked,
        )
    )

    bad_mode_blocked = False
    try:
        SchedulerConfig.from_dict(
            {
                "mode": "UNSAFE_MODE",
            }
        )
    except SchedulerConfigError:
        bad_mode_blocked = True

    tests.append(
        (
            "Unknown scheduler mode fails closed",
            bad_mode_blocked,
        )
    )

    preview_calls = []
    queue_calls = []

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)

        preview_config = SchedulerConfig.from_dict(
            {
                "mode": MODE_PREVIEW,
                "limit": 2,
                "scheduler_artifacts_dir": str(
                    root
                    / "scheduler-preview"
                ),
            }
        )

        preview_report = run_scheduled_browser_queue(
            config=preview_config,
            repository=object(),
            preview_fn=lambda **kwargs: (
                preview_calls.append(kwargs)
                or [
                    {
                        "board_token": "stripe",
                        "greenhouse_job_id": "1",
                        "company": "Stripe",
                        "title": "Backend Engineer",
                        "application_status": "PENDING",
                        "route": "AGENT_APPLY",
                        "score": 70,
                        "confidence": 80,
                        "selected_resume_file": (
                            "private_resume.pdf"
                        ),
                    }
                ]
            ),
            queue_fn=lambda **kwargs: (
                queue_calls.append(kwargs)
                or {}
            ),
        )

        tests.append(
            (
                "PREVIEW does not open the browser queue",
                (
                    len(preview_calls) == 1
                    and not queue_calls
                    and preview_report[
                        "browser_opened"
                    ]
                    is False
                ),
            )
        )

        tests.append(
            (
                "Scheduler preview report excludes resume filename",
                "private_resume.pdf"
                not in json.dumps(
                    preview_report
                ),
            )
        )

        dry_config = SchedulerConfig.from_dict(
            {
                "mode": MODE_BROWSER_DRY_RUN,
                "limit": 1,
                "scheduler_artifacts_dir": str(
                    root
                    / "scheduler-dry"
                ),
                "queue_artifacts_dir": str(
                    root
                    / "queue-dry"
                ),
                "profile_path": str(
                    root
                    / "profile.json"
                ),
            }
        )

        dry_calls = []

        dry_report = run_scheduled_browser_queue(
            config=dry_config,
            repository=object(),
            profile_loader=lambda _path: object(),
            queue_fn=lambda **kwargs: (
                dry_calls.append(kwargs)
                or {
                    "summary": {
                        "selected": 1,
                        "completed": 1,
                        "needs_assistance": 1,
                        "ready_no_submit": 0,
                        "blocked": 0,
                        "errors": 0,
                        "challenge_count": 1,
                    },
                    "results": [
                        {
                            "board_token": "stripe",
                            "greenhouse_job_id": "1",
                            "company": "Stripe",
                            "title": "Backend Engineer",
                            "queue_status": "COMPLETED",
                            "outcome": "NEEDS_ASSISTANCE",
                            "challenge_detected": True,
                            "ready_count": 8,
                            "required_human_count": 6,
                            "browser_modified": False,
                            "error": (
                                "private@example.com"
                            ),
                        }
                    ],
                    "history_persisted": False,
                    "submit_clicked_by_agent": False,
                    "application_submitted": False,
                }
            ),
        )

        tests.append(
            (
                "BROWSER_DRY_RUN is headless and non-persistent",
                (
                    dry_calls[0]["headless"]
                    is True
                    and dry_calls[0]["persist"]
                    is False
                    and dry_calls[0][
                        "include_in_progress"
                    ]
                    is False
                ),
            )
        )

        tests.append(
            (
                "Scheduled result strips arbitrary browser error text",
                "private@example.com"
                not in json.dumps(
                    dry_report
                ),
            )
        )

        persist_config = SchedulerConfig.from_dict(
            {
                "mode": MODE_BROWSER_PERSISTED,
                "scheduler_artifacts_dir": str(
                    root
                    / "scheduler-persist"
                ),
                "queue_artifacts_dir": str(
                    root
                    / "queue-persist"
                ),
                "profile_path": str(
                    root
                    / "profile.json"
                ),
            }
        )

        persisted_blocked = False
        try:
            run_scheduled_browser_queue(
                config=persist_config,
                repository=object(),
            )
        except SchedulerConfigError:
            persisted_blocked = True

        tests.append(
            (
                "Persisted scheduled mode requires second explicit allow flag",
                persisted_blocked,
            )
        )

        persist_calls = []

        persisted_report = run_scheduled_browser_queue(
            config=persist_config,
            allow_persisted_mode=True,
            repository=object(),
            profile_loader=lambda _path: object(),
            queue_fn=lambda **kwargs: (
                persist_calls.append(kwargs)
                or {
                    "summary": {
                        "selected": 1,
                        "completed": 1,
                        "needs_assistance": 1,
                        "ready_no_submit": 0,
                        "blocked": 0,
                        "errors": 0,
                        "challenge_count": 1,
                    },
                    "results": [],
                    "history_persisted": True,
                    "submit_clicked_by_agent": False,
                    "application_submitted": False,
                }
            ),
        )

        tests.append(
            (
                "Explicit persisted mode passes persist=True and remains headless",
                (
                    persist_calls[0]["persist"]
                    is True
                    and persist_calls[0]["headless"]
                    is True
                    and persisted_report[
                        "supabase_queue_history_persisted"
                    ]
                    is True
                ),
            )
        )

        history_missing_blocked = False
        try:
            run_scheduled_browser_queue(
                config=persist_config,
                allow_persisted_mode=True,
                repository=object(),
                profile_loader=lambda _path: object(),
                queue_fn=lambda **kwargs: {
                    "summary": {},
                    "results": [],
                    "history_persisted": False,
                    "submit_clicked_by_agent": False,
                    "application_submitted": False,
                },
            )
        except RuntimeError:
            history_missing_blocked = True

        tests.append(
            (
                "Persisted scheduled mode fails if queue history is not persisted",
                history_missing_blocked,
            )
        )

        submission_blocked = False
        try:
            run_scheduled_browser_queue(
                config=dry_config,
                repository=object(),
                profile_loader=lambda _path: object(),
                queue_fn=lambda **kwargs: {
                    "summary": {},
                    "results": [],
                    "history_persisted": False,
                    "submit_clicked_by_agent": False,
                    "application_submitted": True,
                },
            )
        except RuntimeError:
            submission_blocked = True

        tests.append(
            (
                "Submission invariant violation fails closed",
                submission_blocked,
            )
        )

        lock_path = root / "lock"
        lock_blocked = False

        with SingleRunLock(lock_path):
            try:
                with SingleRunLock(
                    lock_path
                ):
                    pass
            except SchedulerLockHeld:
                lock_blocked = True

        tests.append(
            (
                "Second concurrent scheduled run is blocked by lock",
                lock_blocked,
            )
        )

        plist = build_plist(
            agent_dir=root.resolve(),
            python_path="/usr/bin/python3",
            config_path=(
                "config/browser_scheduler.json"
            ),
            hour=10,
            minute=30,
            allow_persisted_mode=False,
        )

        args = plist[
            "ProgramArguments"
        ]

        tests.append(
            (
                "Generated launchd job does not allow persisted mode by default",
                (
                    "--allow-persisted-mode"
                    not in args
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
                "config/browser_scheduler.json"
            ),
            hour=10,
            minute=30,
            allow_persisted_mode=True,
        )

        tests.append(
            (
                "Persisted launchd command requires explicit generator opt-in",
                "--allow-persisted-mode"
                in persisted_plist[
                    "ProgramArguments"
                ],
            )
        )

    source = Path(
        __import__(
            "src.browser.scheduled_runner",
            fromlist=["dummy"],
        ).__file__
    ).read_text(
        encoding="utf-8"
    ).lower()

    tests.append(
        (
            "Scheduled runner contains no submit/click call path",
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
            "generate_macos_browser_scheduler"
        ).__file__
    ).read_text(
        encoding="utf-8"
    ).lower()

    tests.append(
        (
            "launchd generator executes no system scheduling command",
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
            "Scheduled runner never opts into IN_PROGRESS jobs",
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
        "SCHEDULED BROWSER QUEUE EXECUTION V1 TEST"
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

    failed = len(tests) - passed

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
        raise SystemExit(1)

    print(
        "✅ SCHEDULED BROWSER QUEUE EXECUTION V1 TEST PASSED"
    )
    print("=" * 104)


if __name__ == "__main__":
    main()
