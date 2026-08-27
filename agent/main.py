from src.greenhouse.client import get_jobs

from src.filtering.job_filter import filter_by_role

from src.filtering.location_filter import (
    filter_by_location,
)

from src.filtering.experience_filter import (
    filter_by_experience,
    clean_job_content,
)

from src.matching.resume_loader import (
    load_all_resumes,
)

from src.matching.matcher import (
    rank_resumes,
)


def pretty_name(name: str) -> str:
    return (
        name
        .replace("_", " ")
        .title()
    )


def choose_test_job(
    eligible_jobs: list[dict],
) -> dict | None:
    """
    Prefer a Backend Engineer role for this test.
    """

    for result in eligible_jobs:

        job = result["job"]

        title = job.get(
            "title",
            "",
        ).lower()

        if "backend engineer" in title:
            return result

    if eligible_jobs:
        return eligible_jobs[0]

    return None


def print_group_result(
    group: dict,
) -> None:

    options = " OR ".join(
        group["skills"]
    )

    if group["satisfied"]:

        matches = ", ".join(
            group[
                "matching_options"
            ]
        )

        print(
            f"  ✓ {options}"
            f"  [matched: {matches}]"
        )

    else:

        print(
            f"  ✗ {options}"
        )


def main():

    board_token = "stripe"

    print()
    print("=" * 80)
    print("GREENHOUSE REFINED MATCH SCORE TEST")
    print("=" * 80)

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

    # IMPORTANT:
    #
    # 4-year REVIEW jobs remain eligible.
    #
    # Only experience REJECT jobs are removed.
    eligible_jobs = (
        accepted_jobs
        + review_jobs
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("ELIGIBILITY SUMMARY")
    print("-" * 80)

    print(
        f"Total jobs:                   "
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
        f"Experience accepted:          "
        f"{len(accepted_jobs)}"
    )

    print(
        f"Experience review / eligible: "
        f"{len(review_jobs)}"
    )

    print(
        f"Experience rejected / skip:   "
        f"{len(rejected_jobs)}"
    )

    print(
        f"TOTAL ELIGIBLE FOR APPLY:     "
        f"{len(eligible_jobs)}"
    )

    # ========================================================
    # SELECT TEST JOB
    # ========================================================

    test_result = choose_test_job(
        eligible_jobs
    )

    if not test_result:

        print(
            "No eligible test job found."
        )

        return

    test_job = test_result[
        "job"
    ]

    experience_mentions = (
        test_result[
            "experience_mentions"
        ]
    )

    title = test_job.get(
        "title",
        "Unknown title",
    )

    location = test_job.get(
        "location",
        {},
    ).get(
        "name",
        "Unknown location",
    )

    url = test_job.get(
        "absolute_url",
        "No URL",
    )

    content = test_job.get(
        "content",
        "",
    )

    job_text = clean_job_content(
        content
    )

    # ========================================================
    # JOB
    # ========================================================

    print()
    print("=" * 80)
    print("TEST JOB")
    print("=" * 80)

    print(
        f"Title:    {title}"
    )

    print(
        f"Location: {location}"
    )

    print(
        f"URL:      {url}"
    )

    # ========================================================
    # RESUMES
    # ========================================================

    print()
    print(
        "Loading master resumes..."
    )

    resumes = load_all_resumes()

    print(
        f"Loaded {len(resumes)} "
        f"master resumes."
    )

    # ========================================================
    # MATCH
    # ========================================================

    print()
    print(
        "Calculating refined match scores..."
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

    print()
    print(
        "Detected profile: "
        f"{pretty_name(result['job_profile'])}"
    )

    print(
        "Experience component: "
        f"{result['experience_score']:.2f}"
    )

    # ========================================================
    # JOB REQUIREMENTS
    # ========================================================

    requirements = result[
        "requirements"
    ]

    print()
    print("=" * 80)
    print("JOB REQUIREMENTS")
    print("=" * 80)

    print()
    print("Required:")

    if requirements[
        "required_skills"
    ]:

        for skill in requirements[
            "required_skills"
        ]:
            print(
                f"  • {skill}"
            )

    else:
        print("  None")

    print()
    print("Preferred:")

    if requirements[
        "preferred_skills"
    ]:

        for skill in requirements[
            "preferred_skills"
        ]:
            print(
                f"  • {skill}"
            )

    else:
        print("  None")

    print()
    print("Alternative groups:")

    required_groups_exist = False

    for group in requirements[
        "alternative_groups"
    ]:

        required_groups_exist = True

        print(
            "  • "
            + " OR ".join(
                group["skills"]
            )
            + f" [{group['section']}]"
        )

    if not required_groups_exist:
        print("  None")

    # ========================================================
    # RANKINGS
    # ========================================================

    print()
    print("=" * 80)
    print("REFINED RESUME RANKING")
    print("=" * 80)

    for index, item in enumerate(
        result["rankings"],
        start=1,
    ):

        print()
        print(
            f"{index}. "
            f"{pretty_name(item['resume_name'])}"
        )

        print(
            f"   FINAL:       "
            f"{item['final_score']:.2f}"
        )

        print(
            f"   Role:        "
            f"{item['role_score']:.2f}"
        )

        print(
            f"   Required:    "
            f"{item['required_score']:.2f}"
        )

        print(
            f"   Preferred:   "
            f"{item['preferred_score']:.2f}"
        )

        print(
            f"   Semantic:    "
            f"{item['semantic_score']:.2f}"
            f" "
            f"(raw "
            f"{item['semantic_raw']:.2f})"
        )

        print(
            f"   Experience:  "
            f"{item['experience_score']:.2f}"
        )

        print(
            f"   Route:       "
            f"{item['route']}"
        )

    # ========================================================
    # WINNER DETAILS
    # ========================================================

    best = result[
        "rankings"
    ][0]

    print()
    print("=" * 80)
    print("BEST MATCH")
    print("=" * 80)

    print(
        f"Resume: "
        f"{pretty_name(best['resume_name'])}"
    )

    print(
        f"File: "
        f"{best['filename']}"
    )

    print(
        f"Score: "
        f"{best['final_score']:.2f}/100"
    )

    print(
        f"Route: "
        f"{best['route']}"
    )

    # --------------------------------------------------------
    # REQUIRED DETAIL
    # --------------------------------------------------------

    print()
    print("Required skill matches:")

    if best[
        "matched_required"
    ]:

        for skill in best[
            "matched_required"
        ]:

            print(
                f"  ✓ {skill}"
            )

    if best[
        "missing_required"
    ]:

        for skill in best[
            "missing_required"
        ]:

            print(
                f"  ✗ {skill}"
            )

    for group in best[
        "required_groups"
    ]:

        print_group_result(
            group
        )

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
