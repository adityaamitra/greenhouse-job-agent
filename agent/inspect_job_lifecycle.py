from src.config.company_loader import (
    load_companies,
)

from src.database.repository import (
    JobRepository,
)

from src.greenhouse.client import (
    get_jobs,
)


def main():

    print()
    print(
        "=" * 100
    )
    print(
        "JOB LIFECYCLE V1 — READ-ONLY INSPECTOR"
    )
    print(
        "=" * 100
    )
    print()
    print(
        "No jobs will be modified by this script."
    )

    companies = (
        load_companies()
    )

    repository = (
        JobRepository()
    )

    total_would_mark_inactive = 0
    successful_companies = 0
    skipped_companies = 0

    for index, company in enumerate(
        companies,
        start=1,
    ):

        company_name = (
            company[
                "name"
            ]
        )

        board_token = (
            company[
                "board_token"
            ]
        )

        print()
        print(
            "-" * 100
        )
        print(
            f"[{index}/{len(companies)}] "
            f"{company_name} "
            f"[{board_token}]"
        )
        print(
            "-" * 100
        )

        try:

            jobs = (
                get_jobs(
                    board_token
                )
            )

        except Exception as error:

            skipped_companies += 1

            print(
                f"FETCH FAILED — lifecycle skipped: {error}"
            )

            continue

        if not jobs:

            skipped_companies += 1

            print(
                "Board returned zero jobs. Lifecycle intentionally skipped."
            )

            continue

        live_ids = [
            job.get(
                "id"
            )
            for job
            in jobs
            if job.get(
                "id"
            ) is not None
        ]

        result = (
            repository
            .sync_board_job_lifecycle(
                board_token=(
                    board_token
                ),

                live_greenhouse_job_ids=(
                    live_ids
                ),

                dry_run=True,
            )
        )

        successful_companies += 1

        stale_jobs = (
            result[
                "stale_jobs"
            ]
        )

        stale_count = (
            result[
                "stale_count"
            ]
        )

        total_would_mark_inactive += (
            stale_count
        )

        print(
            f"Live Greenhouse jobs:    {result['live_count']}"
        )

        print(
            f"Tracked active jobs:     {result['tracked_active_count']}"
        )

        print(
            f"Would mark inactive:     {stale_count}"
        )

        if stale_jobs:

            print()
            print(
                "Candidates:"
            )

            for stale_job in stale_jobs:

                print(
                    f"  ✗ {stale_job.get('title', 'Unknown title')}"
                )

                print(
                    f"      Greenhouse ID: "
                    f"{stale_job.get('greenhouse_job_id')}"
                )

                print(
                    f"      Last seen: "
                    f"{stale_job.get('last_seen_at') or '-'}"
                )

                print(
                    f"      URL: "
                    f"{stale_job.get('url') or '-'}"
                )

    print()
    print()
    print(
        "=" * 100
    )
    print(
        "JOB LIFECYCLE INSPECTION COMPLETE"
    )
    print(
        "=" * 100
    )

    print(
        f"Companies inspected:       {successful_companies}"
    )

    print(
        f"Companies safely skipped:  {skipped_companies}"
    )

    print(
        f"Jobs that WOULD go inactive: "
        f"{total_would_mark_inactive}"
    )

    print()
    print(
        "READ-ONLY: no database lifecycle updates were made."
    )
    print(
        "=" * 100
    )


if __name__ == "__main__":

    main()

