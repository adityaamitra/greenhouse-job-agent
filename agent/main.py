from src.greenhouse.client import get_jobs

from src.filtering.job_filter import filter_by_role
from src.filtering.location_filter import filter_by_location
from src.filtering.experience_filter import (
    filter_by_experience,
    clean_job_content,
)

from src.matching.resume_loader import load_all_resumes
from src.matching.matcher import rank_resumes


def pretty_name(name: str) -> str:
    return name.replace("_", " ").title()


def choose_test_job(
    accepted_jobs: list[dict],
) -> dict | None:

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
    print("GREENHOUSE FINAL MATCH SCORE TEST")
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
    # FILTER
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

    print()
    print("FILTER SUMMARY")
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
        f"Experience manual review:     "
        f"{len(review_jobs)}"
    )

    print(
        f"Experience rejected:          "
        f"{len(rejected_jobs)}"
    )

    # ========================================================
    # TEST JOB
    # ========================================================

    test_job = choose_test_job(
        accepted_jobs
    )

    if test_job is None:
        print("No accepted test job available.")
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

    url = test_job.get(
        "absolute_url",
        "No URL",
    )

    job_text = clean_job_content(
        test_job.get(
            "content",
            "",
        )
    )

    print()
    print("=" * 80)
    print("TEST JOB")
    print("=" * 80)

    print(f"Title:    {title}")
    print(f"Location: {location}")
    print(f"URL:      {url}")

    # ========================================================
    # LOAD RESUMES
    # ========================================================

    print()
    print("Loading master resumes...")

    resumes = load_all_resumes()

    print(
        f"Loaded {len(resumes)} master resumes."
    )

    # ========================================================
    # MATCH
    # ========================================================

    print()
    print("Calculating weighted match scores...")

    result = rank_resumes(
        job_title=title,
        job_text=job_text,
        resumes=resumes,
    )

    print()
    print(f"Detected job profile: {pretty_name(result['job_profile'])}")

    print()
    print("JD SKILLS DETECTED")
    print("-" * 80)

    if result["job_skills"]:

        for skill in result["job_skills"]:
            print(f"  • {skill}")

    else:
        print("No known skills detected.")

    # ========================================================
    # RANKING
    # ========================================================

    print()
    print("=" * 80)
    print("FINAL RESUME RANKING")
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
            f"   Final Score:       "
            f"{item['final_score']:.2f}"
        )

        print(
            f"   Role Score:        "
            f"{item['role_score']:.2f}"
        )

        print(
            f"   Skill Score:       "
            f"{item['skill_score']:.2f}"
        )

        print(
            f"   Semantic Score:    "
            f"{item['semantic_score']:.2f}"
            f" "
            f"(raw {item['semantic_raw']:.2f})"
        )

        print(
            f"   Route:             "
            f"{item['route']}"
        )

    # ========================================================
    # BEST MATCH
    # ========================================================

    best = result["rankings"][0]

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
        f"Final score: "
        f"{best['final_score']:.2f}/100"
    )

    print(
        f"Route: "
        f"{best['route']}"
    )

    print()
    print("Matched skills:")

    if best["matched_skills"]:

        for skill in best["matched_skills"]:
            print(f"  ✓ {skill}")

    else:
        print("  None")

    print()
    print("Missing skills:")

    if best["missing_skills"]:

        for skill in best["missing_skills"]:
            print(f"  ✗ {skill}")

    else:
        print("  None")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
