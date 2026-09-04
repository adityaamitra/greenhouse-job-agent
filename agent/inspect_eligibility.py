from src.greenhouse.client import (
    get_jobs,
)

from src.filtering.job_filter import (
    filter_by_role,
)

from src.filtering.employment_filter import (
    filter_by_employment_type,
)

from src.filtering.location_filter import (
    filter_by_location,
)

from src.filtering.experience_filter import (
    filter_by_experience,
    clean_job_content,
)

from src.filtering.eligibility_filter import (
    evaluate_hard_eligibility,
)


BOARD_TOKEN = "scaleai"


def main():

    print()
    print("=" * 90)
    print(
        "ELIGIBILITY EVIDENCE INSPECTOR"
    )
    print("=" * 90)

    jobs = get_jobs(
        BOARD_TOKEN
    )

    role_jobs = filter_by_role(
        jobs
    )

    (
        full_time_jobs,
        _,
    ) = filter_by_employment_type(
        role_jobs
    )

    (
        us_jobs,
        _,
        _,
    ) = filter_by_location(
        full_time_jobs
    )

    (
        accepted_jobs,
        review_jobs,
        _,
    ) = filter_by_experience(
        us_jobs
    )

    eligible_jobs = (
        accepted_jobs
        + review_jobs
    )

    flagged = 0

    for result in eligible_jobs:

        job = result[
            "job"
        ]

        title = job.get(
            "title",
            "Unknown title",
        )

        content = job.get(
            "content",
            "",
        )

        job_text = clean_job_content(
            content
        )

        eligibility = (
            evaluate_hard_eligibility(
                job_title=title,
                job_text=job_text,
            )
        )

        if (
            eligibility[
                "decision"
            ]
            != "NEEDS_ASSISTANCE"
        ):
            continue

        flagged += 1

        print()
        print("=" * 90)

        print(
            f"{flagged}. {title}"
        )

        print("=" * 90)

        print(
            f"Decision: "
            f"{eligibility['decision']}"
        )

        print(
            f"Reason: "
            f"{eligibility['reason']}"
        )

        print()

        for index, finding in enumerate(
            eligibility[
                "findings"
            ],
            start=1,
        ):

            print(
                f"Finding {index}"
            )

            print(
                f"Category: "
                f"{finding['category']}"
            )

            print(
                "Evidence:"
            )

            print(
                finding[
                    "evidence"
                ]
            )

            print()
            print("-" * 90)

        print(
            f"URL: "
            f"{job.get('absolute_url', '')}"
        )

    print()
    print("=" * 90)

    print(
        f"Total flagged jobs: "
        f"{flagged}"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()
