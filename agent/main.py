from src.greenhouse.client import get_jobs

from src.filtering.job_filter import filter_by_role
from src.filtering.location_filter import filter_by_location

from src.filtering.experience_filter import (
    filter_by_experience,
    clean_job_content,
)

from src.matching.resume_loader import (
    load_all_resumes,
)

from src.matching.matcher import (
    rank_resumes,
    infer_job_profile,
)


TARGET_PROFILES = [
    "software_engineer",
    "backend_engineer",
    "frontend_engineer",
    "fullstack_engineer",
    "ai_ml_engineer",
    "systems_engineer",
    "production_support_engineer",
    "devops_engineer",
]


def pretty_name(name: str) -> str:
    return (
        name
        .replace("_", " ")
        .title()
    )


def choose_jobs_by_profile(
    eligible_jobs: list[dict],
) -> dict[str, dict]:
    """
    Pick one eligible job for each available target profile.
    """

    selected = {}

    for result in eligible_jobs:

        job = result["job"]

        title = job.get(
            "title",
            "",
        )

        profile = infer_job_profile(
            title
        )

        if (
            profile in TARGET_PROFILES
            and profile not in selected
        ):
            selected[profile] = result

    return selected


def main():

    board_token = "stripe"

    print()
    print("=" * 90)
    print("MULTI-PROFILE RESUME ROUTER TEST")
    print("=" * 90)

    # ========================================================
    # FETCH
    # ========================================================

    print()
    print(
        f"Fetching Greenhouse jobs for: "
        f"{board_token}"
    )

    jobs = get_jobs(
        board_token
    )

    if not jobs:

        print("No jobs found.")
        return

    # ========================================================
    # ELIGIBILITY
    # ========================================================

    role_jobs = filter_by_role(
        jobs
    )

    (
        us_jobs,
        unknown_location_jobs,
        non_us_jobs,
    ) = filter_by_location(
        role_jobs
    )

    (
        accepted_jobs,
        review_jobs,
        rejected_jobs,
    ) = filter_by_experience(
        us_jobs
    )

    # 4-year review jobs are still eligible.
    eligible_jobs = (
        accepted_jobs
        + review_jobs
    )

    print()
    print("ELIGIBILITY SUMMARY")
    print("-" * 90)

    print(
        f"All Greenhouse jobs:          "
        f"{len(jobs)}"
    )

    print(
        f"Target-role jobs:             "
        f"{len(role_jobs)}"
    )

    print(
        f"US-compatible jobs:           "
        f"{len(us_jobs)}"
    )

    print(
        f"Eligible for application:     "
        f"{len(eligible_jobs)}"
    )

    print(
        f"Experience rejected:          "
        f"{len(rejected_jobs)}"
    )

    # ========================================================
    # PICK TEST JOBS
    # ========================================================

    selected_jobs = choose_jobs_by_profile(
        eligible_jobs
    )

    print()
    print("=" * 90)
    print("AVAILABLE TEST PROFILES")
    print("=" * 90)

    for profile in TARGET_PROFILES:

        if profile in selected_jobs:

            title = (
                selected_jobs[profile]
                ["job"]
                .get(
                    "title",
                    "Unknown title",
                )
            )

            print(
                f"✓ {pretty_name(profile):30} "
                f"→ {title}"
            )

        else:

            print(
                f"✗ {pretty_name(profile):30} "
                f"→ No eligible Stripe job found"
            )

    if not selected_jobs:

        print()
        print("No jobs available for testing.")
        return

    # ========================================================
    # LOAD RESUMES ONCE
    # ========================================================

    print()
    print("Loading master resumes...")

    resumes = load_all_resumes()

    print(
        f"Loaded {len(resumes)} master resumes."
    )

    # ========================================================
    # TEST EVERY AVAILABLE PROFILE
    # ========================================================

    summary = []

    for profile in TARGET_PROFILES:

        if profile not in selected_jobs:
            continue

        test_result = selected_jobs[
            profile
        ]

        job = test_result[
            "job"
        ]

        experience_mentions = (
            test_result[
                "experience_mentions"
            ]
        )

        title = job.get(
            "title",
            "Unknown title",
        )

        location = job.get(
            "location",
            {},
        ).get(
            "name",
            "Unknown location",
        )

        content = job.get(
            "content",
            "",
        )

        job_text = clean_job_content(
            content
        )

        print()
        print()
        print("=" * 90)
        print(
            f"TESTING: {pretty_name(profile)}"
        )
        print("=" * 90)

        print(
            f"Job:      {title}"
        )

        print(
            f"Location: {location}"
        )

        print()
        print(
            "Calculating scores..."
        )

        result = rank_resumes(
            job_title=title,
            job_content=content,
            job_text=job_text,
            experience_mentions=(
                experience_mentions
            ),
            resumes=resumes,
        )

        rankings = result[
            "rankings"
        ]

        # ----------------------------------------------------
        # PRINT TOP 3
        # ----------------------------------------------------

        print()
        print("TOP 3 RESUMES")
        print("-" * 90)

        for index, item in enumerate(
            rankings[:3],
            start=1,
        ):

            print(
                f"{index}. "
                f"{pretty_name(item['resume_name']):30} "
                f"{item['final_score']:6.2f} "
                f"→ {item['route']}"
            )

        winner = rankings[0]

        expected_resume = profile

        correct = (
            winner[
                "resume_name"
            ]
            == expected_resume
        )

        summary.append(
            {
                "profile": profile,
                "job_title": title,
                "expected": expected_resume,
                "winner": winner[
                    "resume_name"
                ],
                "score": winner[
                    "final_score"
                ],
                "route": winner[
                    "route"
                ],
                "correct": correct,
            }
        )

        print()
        print(
            f"Expected profile resume: "
            f"{pretty_name(expected_resume)}"
        )

        print(
            f"Selected resume:         "
            f"{pretty_name(winner['resume_name'])}"
        )

        print(
            f"Router result:           "
            f"{'✓ CORRECT' if correct else '✗ NEEDS REVIEW'}"
        )

    # ========================================================
    # FINAL ROUTER SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 90)
    print("ROUTER VALIDATION SUMMARY")
    print("=" * 90)

    correct_count = sum(
        1
        for item in summary
        if item["correct"]
    )

    total_count = len(
        summary
    )

    for item in summary:

        marker = (
            "✓"
            if item["correct"]
            else "✗"
        )

        print()

        print(
            f"{marker} "
            f"{pretty_name(item['profile'])}"
        )

        print(
            f"   Job:      "
            f"{item['job_title']}"
        )

        print(
            f"   Expected: "
            f"{pretty_name(item['expected'])}"
        )

        print(
            f"   Selected: "
            f"{pretty_name(item['winner'])}"
        )

        print(
            f"   Score:    "
            f"{item['score']:.2f}"
        )

        print(
            f"   Route:    "
            f"{item['route']}"
        )

    print()
    print("-" * 90)

    print(
        f"Correct resume selections: "
        f"{correct_count}/{total_count}"
    )

    if total_count:

        accuracy = (
            correct_count
            / total_count
        ) * 100

        print(
            f"Router accuracy on this sample: "
            f"{accuracy:.1f}%"
        )

    print("=" * 90)


if __name__ == "__main__":
    main()
