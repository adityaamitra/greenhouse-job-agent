from src.greenhouse.client import get_jobs
from src.filtering.job_filter import filter_by_role
from src.filtering.location_filter import filter_by_location
from src.filtering.experience_filter import filter_by_experience


def print_job(job: dict) -> None:
    title = job.get("title", "Unknown title")
    location = job.get("location", {}).get("name", "Unknown location")
    job_id = job.get("id", "Unknown ID")
    url = job.get("absolute_url", "No URL")

    print(f"Title: {title}")
    print(f"Location: {location}")
    print(f"Job ID: {job_id}")
    print(f"URL: {url}")


def print_experience_mentions(mentions: list[dict]) -> None:

    if not mentions:
        print("Experience requirement detected: None")
        return

    print("Experience mentions:")

    for mention in mentions:

        print(
            f"  - {mention['match']} "
            f"| min={mention['min_years']} "
            f"| max={mention['max_years']} "
            f"| preferred={mention['preferred']}"
        )

        print(f"    Context: {mention['text']}")


def main():

    board_token = "stripe"

    print()
    print(f"Fetching Greenhouse jobs for: {board_token}")
    print("=" * 70)

    jobs = get_jobs(board_token)

    if not jobs:
        print("No jobs found.")
        return

    # ---------------------------------------------------------
    # ROLE FILTER
    # ---------------------------------------------------------

    role_jobs = filter_by_role(jobs)

    # ---------------------------------------------------------
    # LOCATION FILTER
    # ---------------------------------------------------------

    us_jobs, unknown_location_jobs, non_us_jobs = filter_by_location(
        role_jobs
    )

    # ---------------------------------------------------------
    # EXPERIENCE FILTER
    # ---------------------------------------------------------

    accepted_jobs, review_jobs, rejected_jobs = filter_by_experience(
        us_jobs
    )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    print(f"Total Greenhouse jobs:       {len(jobs)}")
    print(f"Target-role jobs:            {len(role_jobs)}")
    print(f"US-compatible jobs:          {len(us_jobs)}")
    print(f"Unknown-location jobs:       {len(unknown_location_jobs)}")
    print(f"Non-US jobs removed:         {len(non_us_jobs)}")
    print()

    print(f"Experience ACCEPT:           {len(accepted_jobs)}")
    print(f"Experience REVIEW:           {len(review_jobs)}")
    print(f"Experience REJECT:           {len(rejected_jobs)}")

    print("=" * 70)

    # ---------------------------------------------------------
    # REVIEW
    # ---------------------------------------------------------

    if review_jobs:

        print()
        print("=" * 70)
        print("EXPERIENCE — MANUAL REVIEW")
        print("=" * 70)

        for index, result in enumerate(review_jobs, start=1):

            print()
            print(f"{index}.")

            print_job(result["job"])
            print_experience_mentions(
                result["experience_mentions"]
            )

            print("-" * 70)

    # ---------------------------------------------------------
    # REJECT
    # ---------------------------------------------------------

    if rejected_jobs:

        print()
        print("=" * 70)
        print("EXPERIENCE — REJECTED")
        print("=" * 70)

        for index, result in enumerate(rejected_jobs, start=1):

            print()
            print(f"{index}.")

            print_job(result["job"])
            print_experience_mentions(
                result["experience_mentions"]
            )

            print("-" * 70)

    # ---------------------------------------------------------
    # ACCEPT
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("JOBS PASSING EXPERIENCE FILTER")
    print("=" * 70)

    for index, result in enumerate(accepted_jobs, start=1):

        job = result["job"]

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

        url = job.get(
            "absolute_url",
            "No URL",
        )

        print()
        print(f"{index}. {title}")
        print(f"   Location: {location}")
        print(f"   URL: {url}")

    # ---------------------------------------------------------
    # FINAL SUMMARY
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    print(f"Starting jobs:               {len(jobs)}")
    print(f"Target roles:                {len(role_jobs)}")
    print(f"US-compatible:               {len(us_jobs)}")
    print(f"Experience accepted:         {len(accepted_jobs)}")
    print(f"Experience review:           {len(review_jobs)}")
    print(f"Experience rejected:         {len(rejected_jobs)}")

    print("=" * 70)


if __name__ == "__main__":
    main()
