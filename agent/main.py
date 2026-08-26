from src.greenhouse.client import get_jobs
from src.filtering.job_filter import filter_by_role
from src.filtering.location_filter import filter_by_location


def print_job(index: int, job: dict) -> None:
    title = job.get("title", "Unknown title")
    location = job.get("location", {}).get("name", "Unknown location")
    job_id = job.get("id", "Unknown ID")
    url = job.get("absolute_url", "No URL")

    print(f"{index}. {title}")
    print(f"   Location: {location}")
    print(f"   Job ID: {job_id}")
    print(f"   URL: {url}")
    print()


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
    # STEP 1: All jobs
    # ---------------------------------------------------------

    print(f"Total open jobs: {len(jobs)}")

    # ---------------------------------------------------------
    # STEP 2: Target-role filtering
    # ---------------------------------------------------------

    role_jobs = filter_by_role(jobs)

    print(f"Target-role jobs: {len(role_jobs)}")

    # ---------------------------------------------------------
    # STEP 3: Location filtering
    # ---------------------------------------------------------

    us_jobs, unknown_jobs, non_us_jobs = filter_by_location(role_jobs)

    print(f"US-compatible jobs: {len(us_jobs)}")
    print(f"Unknown-location jobs: {len(unknown_jobs)}")
    print(f"Non-US jobs removed: {len(non_us_jobs)}")

    print("=" * 70)

    # ---------------------------------------------------------
    # US JOBS
    # ---------------------------------------------------------

    print()
    print("US-COMPATIBLE JOBS")
    print("=" * 70)
    print()

    if not us_jobs:
        print("No US-compatible target jobs found.")
    else:
        for index, job in enumerate(us_jobs, start=1):
            print_job(index, job)

    # ---------------------------------------------------------
    # UNKNOWN JOBS
    # ---------------------------------------------------------

    if unknown_jobs:
        print()
        print("=" * 70)
        print("UNKNOWN LOCATION — NEEDS FURTHER REVIEW")
        print("=" * 70)
        print()

        for index, job in enumerate(unknown_jobs, start=1):
            print_job(index, job)

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("FILTER SUMMARY")
    print("=" * 70)

    print(f"Total Greenhouse jobs:       {len(jobs)}")
    print(f"Target-role jobs:            {len(role_jobs)}")
    print(f"US-compatible jobs:          {len(us_jobs)}")
    print(f"Unknown-location jobs:       {len(unknown_jobs)}")
    print(f"Non-US jobs removed:         {len(non_us_jobs)}")

    print("=" * 70)


if __name__ == "__main__":
    main()
