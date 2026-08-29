from src.filtering.eligibility_filter import (
    evaluate_hard_eligibility,
)


TEST_CASES = [
    # ========================================================
    # SHOULD PASS
    # ========================================================

    (
        "Software Engineer, Public Sector",
        (
            "You will build software used by public-sector "
            "customers."
        ),
        "PASS",
    ),

    (
        "Backend Engineer",
        "No security clearance required for this position.",
        "PASS",
    ),

    (
        "Software Engineer",
        (
            "Applicants are considered regardless of "
            "citizenship."
        ),
        "PASS",
    ),

    (
        "Software Engineer - Smart Contract",
        (
            "Build blockchain infrastructure and smart "
            "contract systems."
        ),
        "PASS",
    ),

    (
        "Software Engineer",
        (
            "Candidates must be legally authorized to work "
            "in the United States."
        ),
        "PASS",
    ),

    # ========================================================
    # SHOULD REQUIRE ASSISTANCE
    # ========================================================

    (
        "Software Engineer",
        "U.S. citizenship is required for this position.",
        "NEEDS_ASSISTANCE",
    ),

    (
        "Infrastructure Engineer",
        (
            "Candidates must currently hold an active "
            "Top Secret clearance."
        ),
        "NEEDS_ASSISTANCE",
    ),

    (
        "Software Engineer",
        (
            "Must be eligible to obtain a Secret "
            "security clearance."
        ),
        "NEEDS_ASSISTANCE",
    ),

    (
        "Backend Engineer",
        (
            "We are unable to provide visa sponsorship "
            "for this position."
        ),
        "NEEDS_ASSISTANCE",
    ),

    (
        "Systems Engineer",
        (
            "Due to ITAR requirements, applicants must "
            "qualify as a U.S. person."
        ),
        "NEEDS_ASSISTANCE",
    ),

    (
        "Network Engineer",
        (
            "A current professional certification "
            "is required."
        ),
        "NEEDS_ASSISTANCE",
    ),
]


def main():

    print()
    print("=" * 90)
    print(
        "HARD ELIGIBILITY FILTER TEST"
    )
    print("=" * 90)

    passed = 0

    failed = 0

    for index, (
        title,
        description,
        expected,
    ) in enumerate(
        TEST_CASES,
        start=1,
    ):

        result = (
            evaluate_hard_eligibility(
                job_title=title,
                job_text=description,
            )
        )

        actual = (
            result[
                "decision"
            ]
        )

        success = (
            actual
            == expected
        )

        if success:

            passed += 1

            status = "✅ PASS"

        else:

            failed += 1

            status = "❌ FAIL"

        print()
        print(
            f"{index:02}. {status}"
        )

        print(
            f"    Title:    {title}"
        )

        print(
            f"    Expected: {expected}"
        )

        print(
            f"    Actual:   {actual}"
        )

        if result[
            "findings"
        ]:

            for finding in (
                result[
                    "findings"
                ]
            ):

                print(
                    f"    Finding:  "
                    f"{finding['category']}"
                )

    print()
    print("=" * 90)

    print(
        f"Passed: "
        f"{passed}/{len(TEST_CASES)}"
    )

    print(
        f"Failed: "
        f"{failed}/{len(TEST_CASES)}"
    )

    print()

    if failed == 0:

        print(
            "✅ HARD ELIGIBILITY FILTER TEST PASSED"
        )

    else:

        print(
            "❌ HARD ELIGIBILITY FILTER NEEDS ADJUSTMENT"
        )

    print("=" * 90)


if __name__ == "__main__":
    main()
