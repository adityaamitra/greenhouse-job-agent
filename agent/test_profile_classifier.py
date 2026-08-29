from src.matching.profile_classifier import (
    classify_job_profile,
)


TEST_CASES = [
    # ========================================================
    # SCALE AI CASES
    # ========================================================

    (
        "DevOps Engineer, Infrastructure & Security",
        "devops_engineer",
    ),

    (
        "Forward Deployed Software Engineer, Public Sector",
        "software_engineer",
    ),

    (
        "IT Systems Engineer",
        "systems_engineer",
    ),

    (
        "Software Engineer - AI Enablement",
        "ai_ml_engineer",
    ),

    (
        "Software Engineer, ARC Team",
        "software_engineer",
    ),

    (
        "Software Engineer, Enterprise AI",
        "ai_ml_engineer",
    ),

    (
        "Software Engineer, Frontier AI Infrastructure",
        "ai_ml_engineer",
    ),

    (
        "Software Engineer, Gen AI",
        "ai_ml_engineer",
    ),

    (
        "Software Engineer, Identity",
        "software_engineer",
    ),

    (
        "Software Engineer, Platform",
        "software_engineer",
    ),

    (
        "Software Engineer, Public Sector",
        "software_engineer",
    ),

    (
        "Infrastructure Software Engineer, Enterprise GenAI",
        "ai_ml_engineer",
    ),

    # ========================================================
    # STRIPE CASES
    # ========================================================

    (
        "Backend Engineer, Core Technology",
        "backend_engineer",
    ),

    (
        "Frontend Engineer, Payments & Risk",
        "frontend_engineer",
    ),

    (
        "Full Stack Engineer, Bridge",
        "fullstack_engineer",
    ),

    (
        "Machine Learning Engineer",
        "ai_ml_engineer",
    ),

    (
        "Machine Learning Engineer, Radar",
        "ai_ml_engineer",
    ),

    (
        "AI Engineer",
        "ai_ml_engineer",
    ),

    (
        "Software Engineer, Authorization Infrastructure",
        "software_engineer",
    ),

    # ========================================================
    # FIGMA CASES
    # ========================================================

    (
        "Software Engineer - Full Stack",
        "fullstack_engineer",
    ),

    (
        "Software Engineer - C++",
        "software_engineer",
    ),

    (
        "Software Engineer - Growth & Monetization",
        "software_engineer",
    ),

    (
        "Software Engineer - Mobile Web",
        "software_engineer",
    ),

    # ========================================================
    # GENERAL CASES
    # ========================================================

    (
        "Site Reliability Engineer",
        "devops_engineer",
    ),

    (
        "Production Support Engineer",
        "production_support_engineer",
    ),

    (
        "Application Support Engineer",
        "production_support_engineer",
    ),

    (
        "Machine Learning Platform Engineer",
        "ai_ml_engineer",
    ),

    (
        "Generative AI Engineer",
        "ai_ml_engineer",
    ),

    (
        "LLM Engineer",
        "ai_ml_engineer",
    ),
]


def pretty(
    profile: str,
) -> str:

    return (
        profile
        .replace("_", " ")
        .title()
    )


def main():

    print()
    print("=" * 90)
    print(
        "PROFILE CLASSIFIER TEST"
    )
    print("=" * 90)

    passed = 0

    failed = 0

    for index, (
        title,
        expected,
    ) in enumerate(
        TEST_CASES,
        start=1,
    ):

        actual = (
            classify_job_profile(
                title
            )
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
            f"{index:02}. "
            f"{status}"
        )

        print(
            f"    Title:    "
            f"{title}"
        )

        print(
            f"    Expected: "
            f"{pretty(expected)}"
        )

        print(
            f"    Actual:   "
            f"{pretty(actual)}"
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
            "✅ PROFILE CLASSIFIER TEST PASSED"
        )

    else:

        print(
            "❌ PROFILE CLASSIFIER NEEDS ADJUSTMENT"
        )

    print("=" * 90)


if __name__ == "__main__":
    main()
