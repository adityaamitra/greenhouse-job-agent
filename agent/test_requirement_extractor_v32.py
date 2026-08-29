from src.matching.requirement_extractor import (
    extract_requirements,
)


def assert_contains(
    values,
    expected,
    message,
):

    if expected not in values:

        raise AssertionError(
            f"{message}: "
            f"expected {expected}, "
            f"got {values}"
        )


def assert_not_contains(
    values,
    unexpected,
    message,
):

    if unexpected in values:

        raise AssertionError(
            f"{message}: "
            f"unexpected {unexpected}, "
            f"got {values}"
        )


def find_group(
    result,
    skills,
    section="required",
):

    expected = set(
        skills
    )

    for group in result.get(
        "requirement_groups",
        [],
    ):

        if (
            group.get(
                "section"
            )
            == section

            and set(
                group.get(
                    "skills",
                    [],
                )
            )
            == expected
        ):

            return group

    raise AssertionError(
        f"Group not found: {expected}. "
        f"Got {result.get('requirement_groups', [])}"
    )


def test_legal_boilerplate():

    content = """
    <p>
        Figma provides paid sick leave, holidays, and other
        leave benefits in compliance with applicable federal,
        state, and local laws, including the requirements of
        the Washington Minimum Wage Act.
    </p>
    """

    result = (
        extract_requirements(
            content
        )
    )

    assert_not_contains(
        result[
            "required_skills"
        ],
        "Security",
        (
            "Legal compliance text must not create "
            "a required Security skill"
        ),
    )


def test_sentence_scope():

    content = """
    <p>
        We are looking for a strong engineer to join our team.
        The ideal candidate will have experience with
        large-scale distributed systems.
        You will work across backend and frontend and interact
        with LLMs and ML models.
    </p>
    """

    result = (
        extract_requirements(
            content
        )
    )

    assert_contains(
        result[
            "required_skills"
        ],
        "Distributed Systems",
        (
            "Distributed Systems should be required"
        ),
    )

    assert_not_contains(
        result[
            "required_skills"
        ],
        "LLMs",
        (
            "LLM responsibility must not inherit the "
            "previous sentence's requirement classification"
        ),
    )

    assert_contains(
        result[
            "general_skills"
        ],
        "LLMs",
        (
            "LLMs should remain general context"
        ),
    )


def test_experience_working_fluently():

    content = """
    <p>
        Experience working fluently with standard
        containerization and deployment technologies like
        Kubernetes, Terraform, Docker, etc.
    </p>
    """

    result = (
        extract_requirements(
            content
        )
    )

    group = (
        find_group(
            result,
            {
                "Kubernetes",
                "Terraform",
                "Docker",
            },
        )
    )

    if (
        group.get(
            "min_matches"
        )
        != 1
    ):

        raise AssertionError(
            "Technology example group should require one match"
        )


def run_test(
    number,
    name,
    function,
):

    try:

        function()

        print(
            f"{number:02}. ✅ PASS — {name}"
        )

        return True

    except Exception as error:

        print(
            f"{number:02}. ❌ FAIL — {name}"
        )

        print(
            f"    {error}"
        )

        return False


def main():

    print()
    print("=" * 90)
    print(
        "REQUIREMENT EXTRACTOR V3.2 REGRESSION TEST"
    )
    print("=" * 90)
    print()

    tests = [
        (
            "Legal boilerplate does not become required",
            test_legal_boilerplate,
        ),

        (
            "Requirement classification stays sentence scoped",
            test_sentence_scope,
        ),

        (
            "Experience working fluently is required",
            test_experience_working_fluently,
        ),
    ]

    passed = 0

    for index, (
        name,
        function,
    ) in enumerate(
        tests,
        start=1,
    ):

        if run_test(
            index,
            name,
            function,
        ):

            passed += 1

    failed = (
        len(
            tests
        )
        - passed
    )

    print()
    print("=" * 90)

    print(
        f"Passed: {passed}/{len(tests)}"
    )

    print(
        f"Failed: {failed}/{len(tests)}"
    )

    print()

    if failed == 0:

        print(
            "✅ REQUIREMENT EXTRACTOR V3.2 REGRESSION TEST PASSED"
        )

    else:

        print(
            "❌ REQUIREMENT EXTRACTOR V3.2 NEEDS ADJUSTMENT"
        )

    print("=" * 90)


if __name__ == "__main__":

    main()
