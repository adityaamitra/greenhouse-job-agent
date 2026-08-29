import sys

from urllib.parse import (
    parse_qs,
    urlparse,
)

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
)


def extract_board_token(
    value: str,
) -> str:
    """
    Accept either a Greenhouse board token
    or a Greenhouse URL.

    Examples:

        stripe

        https://job-boards.greenhouse.io/stripe

        https://boards.greenhouse.io/stripe

        https://boards.greenhouse.io/embed/job_board?for=stripe
    """

    value = (
        value.strip()
    )

    if not value:

        raise ValueError(
            "Board token or URL "
            "cannot be empty."
        )

    # ========================================================
    # PLAIN TOKEN
    # ========================================================

    if not value.startswith(
        (
            "http://",
            "https://",
        )
    ):

        return (
            value
            .strip("/")
        )

    # ========================================================
    # URL
    # ========================================================

    parsed = (
        urlparse(
            value
        )
    )

    host = (
        parsed.netloc
        .lower()
    )

    if (
        "greenhouse.io"
        not in host
    ):

        raise ValueError(
            "This does not appear "
            "to be a Greenhouse URL."
        )

    # --------------------------------------------------------
    # EMBED FORM
    #
    # boards.greenhouse.io/embed/job_board?for=stripe
    # --------------------------------------------------------

    query = (
        parse_qs(
            parsed.query
        )
    )

    if (
        "for"
        in query
    ):

        values = (
            query["for"]
        )

        if values:

            return (
                values[0]
            )

    # --------------------------------------------------------
    # PATH FORM
    #
    # job-boards.greenhouse.io/stripe
    # boards.greenhouse.io/stripe
    # --------------------------------------------------------

    path_parts = [
        part
        for part
        in parsed.path.split("/")
        if part
    ]

    if not path_parts:

        raise ValueError(
            "Could not determine "
            "a Greenhouse board token "
            "from this URL."
        )

    ignored = {
        "embed",
        "job_board",
        "jobs",
    }

    for part in path_parts:

        if (
            part.lower()
            not in ignored
        ):

            return (
                part
            )

    raise ValueError(
        "Could not determine "
        "the Greenhouse board token."
    )


def validate_company(
    input_value: str,
) -> None:

    print()
    print("=" * 80)
    print(
        "GREENHOUSE COMPANY VALIDATOR"
    )
    print("=" * 80)

    # ========================================================
    # TOKEN
    # ========================================================

    try:

        board_token = (
            extract_board_token(
                input_value
            )
        )

    except ValueError as error:

        print()
        print(
            "❌ INVALID INPUT"
        )

        print(
            f"Reason: {error}"
        )

        return

    print()
    print(
        f"Board token: "
        f"{board_token}"
    )

    print()
    print(
        "Testing Greenhouse board..."
    )

    # ========================================================
    # FETCH
    # ========================================================

    try:

        jobs = (
            get_jobs(
                board_token
            )
        )

    except Exception as error:

        print()
        print(
            "❌ BOARD FETCH FAILED"
        )

        print(
            f"Error type: "
            f"{type(error).__name__}"
        )

        print(
            f"Error: {error}"
        )

        return

    if not jobs:

        print()
        print(
            "❌ BOARD RETURNED NO JOBS"
        )

        return

    # ========================================================
    # COMPANY NAME
    # ========================================================

    detected_company = None

    for job in jobs:

        company_name = (
            job.get(
                "company_name"
            )
        )

        if company_name:

            detected_company = (
                company_name
            )

            break

    # ========================================================
    # TARGET ROLE FILTER
    # ========================================================

    role_jobs = (
        filter_by_role(
            jobs
        )
    )

    # ========================================================
    # FULL-TIME FILTER
    # ========================================================

    (
        full_time_jobs,
        employment_rejected_jobs,
    ) = filter_by_employment_type(
        role_jobs
    )

    # ========================================================
    # LOCATION FILTER
    # ========================================================

    (
        us_jobs,
        unknown_location_jobs,
        non_us_jobs,
    ) = filter_by_location(
        full_time_jobs
    )

    # ========================================================
    # EXPERIENCE FILTER
    # ========================================================

    (
        accepted_jobs,
        review_jobs,
        rejected_jobs,
    ) = filter_by_experience(
        us_jobs
    )

    eligible_jobs = (
        accepted_jobs
        + review_jobs
    )

    # ========================================================
    # RESULTS
    # ========================================================

    print()
    print("=" * 80)
    print(
        "VALIDATION RESULT"
    )
    print("=" * 80)

    print()
    print(
        "Board status:           "
        "✅ VALID"
    )

    print(
        f"Detected company:       "
        f"{detected_company or 'Not provided by API'}"
    )

    print(
        f"Board token:            "
        f"{board_token}"
    )

    print()
    print(
        f"Jobs returned:          "
        f"{len(jobs)}"
    )

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
        f"{len(employment_rejected_jobs)}"
    )

    print(
        f"US-compatible jobs:     "
        f"{len(us_jobs)}"
    )

    print(
        f"Unknown-location jobs:  "
        f"{len(unknown_location_jobs)}"
    )

    print(
        f"Non-US jobs removed:    "
        f"{len(non_us_jobs)}"
    )

    print(
        f"Experience accepted:    "
        f"{len(accepted_jobs)}"
    )

    print(
        f"Experience review:      "
        f"{len(review_jobs)}"
    )

    print(
        f"Experience filtered:    "
        f"{len(rejected_jobs)}"
    )

    print(
        f"TOTAL ELIGIBLE:         "
        f"{len(eligible_jobs)}"
    )

    # ========================================================
    # EMPLOYMENT-TYPE DEBUG
    # ========================================================

    if employment_rejected_jobs:

        print()
        print("-" * 80)
        print(
            "EMPLOYMENT-TYPE EXCLUSIONS"
        )
        print("-" * 80)

        for index, item in enumerate(
            employment_rejected_jobs,
            start=1,
        ):

            job = (
                item["job"]
            )

            classification = (
                item[
                    "classification"
                ]
            )

            print()

            print(
                f"{index}. "
                f"{job.get('title', 'Unknown title')}"
            )

            print(
                f"   Reason:   "
                f"{classification['reason']}"
            )

            print(
                f"   Evidence: "
                f"{classification.get('evidence') or '-'}"
            )

    # ========================================================
    # FINAL RECOMMENDATION
    # ========================================================

    print()

    if eligible_jobs:

        print(
            "✅ WORTH ADDING TO SCANNER"
        )

    elif role_jobs:

        if (
            employment_rejected_jobs
            and not full_time_jobs
        ):

            print(
                "⚠️ Valid board, but current "
                "target roles are not full-time."
            )

        else:

            print(
                "⚠️ Valid board, but no "
                "currently eligible jobs."
            )

    else:

        print(
            "⚠️ Valid board, but no "
            "current target-role jobs."
        )

    print()
    print("=" * 80)


def main():

    if (
        len(sys.argv)
        < 2
    ):

        print()
        print(
            "Usage:"
        )

        print()
        print(
            "  python validate_company.py "
            "<board-token-or-greenhouse-url>"
        )

        print()
        print(
            "Examples:"
        )

        print()
        print(
            "  python validate_company.py "
            "stripe"
        )

        print()
        print(
            "  python validate_company.py "
            "https://job-boards.greenhouse.io/stripe"
        )

        return

    input_value = (
        sys.argv[1]
    )

    validate_company(
        input_value
    )


if __name__ == "__main__":
    main()
