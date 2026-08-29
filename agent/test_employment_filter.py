from src.greenhouse.client import (
    get_jobs,
)

from src.filtering.job_filter import (
    filter_by_role,
)

from src.filtering.employment_filter import (
    filter_by_employment_type,
)


def main():

    print()
    print("=" * 80)
    print(
        "FULL-TIME EMPLOYMENT FILTER TEST"
    )
    print("=" * 80)

    board_token = "figma"

    print()
    print(
        f"Fetching: {board_token}"
    )

    jobs = get_jobs(
        board_token
    )

    role_jobs = filter_by_role(
        jobs
    )

    (
        full_time_jobs,
        rejected_jobs,
    ) = filter_by_employment_type(
        role_jobs
    )

    print()
    print(
        f"Target-role jobs:       "
        f"{len(role_jobs)}"
    )

    print(
        f"Full-time candidates:   "
        f"{len(full_time_jobs)}"
    )

    print(
        f"Employment filtered:    "
        f"{len(rejected_jobs)}"
    )

    print()
    print("=" * 80)
    print(
        "EMPLOYMENT-FILTERED JOBS"
    )
    print("=" * 80)

    if not rejected_jobs:

        print()
        print(
            "None"
        )

    for index, item in enumerate(
        rejected_jobs,
        start=1,
    ):

        job = item[
            "job"
        ]

        classification = item[
            "classification"
        ]

        print()
        print(
            f"{index}. "
            f"{job.get('title', 'Unknown')}"
        )

        print(
            f"   Reason:   "
            f"{classification['reason']}"
        )

        print(
            f"   Evidence: "
            f"{classification['evidence']}"
        )

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
