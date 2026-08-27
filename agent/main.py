from src.greenhouse.client import get_jobs

from src.filtering.job_filter import filter_by_role
from src.filtering.location_filter import filter_by_location
from src.filtering.experience_filter import filter_by_experience

from src.matching.requirement_extractor import (
    extract_requirements,
)


def choose_test_job(
    accepted_jobs: list[dict],
) -> dict | None:
    """
    Choose a Backend Engineer job for our requirement parser test.
    """

    for result in accepted_jobs:

        job = result["job"]

        title = job.get(
            "title",
            "",
        ).lower()

        if "backend engineer" in title:
            return job

    if accepted_jobs:
        return accepted_jobs[0]["job"]

    return None


def main():

    board_token = "stripe"

    print()
    print("=" * 80)
    print("GREENHOUSE REQUIREMENT EXTRACTOR TEST")
    print("=" * 80)

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

    test_job = choose_test_job(
        accepted_jobs
    )

    if not test_job:
        print("No accepted test job found.")
        return

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

    print()
    print("=" * 80)
    print("TEST JOB")
    print("=" * 80)

    print(f"Title:    {title}")
    print(f"Location: {location}")

    result = extract_requirements(
        test_job.get(
            "content",
            "",
        )
    )

    # ========================================================
    # REQUIRED
    # ========================================================

    print()
    print("=" * 80)
    print("REQUIRED SKILLS")
    print("=" * 80)

    if result["required_skills"]:

        for skill in result[
            "required_skills"
        ]:
            print(f"  ✓ {skill}")

    else:
        print("  None detected")

    # ========================================================
    # PREFERRED
    # ========================================================

    print()
    print("=" * 80)
    print("PREFERRED SKILLS")
    print("=" * 80)

    if result["preferred_skills"]:

        for skill in result[
            "preferred_skills"
        ]:
            print(f"  • {skill}")

    else:
        print("  None detected")

    # ========================================================
    # GENERAL
    # ========================================================

    print()
    print("=" * 80)
    print("GENERAL JD MENTIONS")
    print("=" * 80)

    if result["general_skills"]:

        for skill in result[
            "general_skills"
        ]:
            print(f"  • {skill}")

    else:
        print("  None detected")

    # ========================================================
    # ALTERNATIVES
    # ========================================================

    print()
    print("=" * 80)
    print("ALTERNATIVE SKILL GROUPS")
    print("=" * 80)

    if result["alternative_groups"]:

        for group in result[
            "alternative_groups"
        ]:

            print()

            print(
                f"Section: "
                f"{group['section']}"
            )

            print(
                "Skills: "
                + " OR ".join(
                    group["skills"]
                )
            )

            print(
                f"Context: "
                f"{group['text']}"
            )

    else:
        print("  None detected")

    # ========================================================
    # EVIDENCE
    # ========================================================

    print()
    print("=" * 80)
    print("DETECTION EVIDENCE")
    print("=" * 80)

    for item in result["evidence"]:

        print()
        print(
            f"[{item['section'].upper()}]"
        )

        print(
            "Skills: "
            + ", ".join(
                item["skills"]
            )
        )

        print(
            f"Text: {item['text']}"
        )

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
