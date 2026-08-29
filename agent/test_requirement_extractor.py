from src.matching.requirement_extractor import (
    extract_requirements,
    extract_skills,
)

from src.matching.matcher import (
    calculate_requirement_score,
)


# ============================================================
# ASSERT HELPERS
# ============================================================

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


def assert_equal(
    actual,
    expected,
    message,
):

    if actual != expected:

        raise AssertionError(
            f"{message}: "
            f"expected {expected}, "
            f"got {actual}"
        )


def get_groups(
    result: dict,
    section: str,
) -> list[dict]:

    return [
        group

        for group
        in result.get(
            "requirement_groups",
            [],
        )

        if (
            group.get(
                "section"
            )
            == section
        )
    ]


def find_group(
    result: dict,
    expected_skills: set[str],
    section: str = "required",
):

    for group in get_groups(
        result,
        section,
    ):

        if (
            set(
                group.get(
                    "skills",
                    [],
                )
            )
            == expected_skills
        ):

            return group

    raise AssertionError(
        (
            f"Could not find {section} group "
            f"{sorted(expected_skills)}. "
            f"Groups were: "
            f"{result.get('requirement_groups', [])}"
        )
    )


# ============================================================
# TEST RUNNER
# ============================================================

def run_test(
    number: int,
    name: str,
    function,
) -> bool:

    try:

        function()

        print(
            f"{number:02}. "
            f"✅ PASS — "
            f"{name}"
        )

        return True

    except Exception as error:

        print(
            f"{number:02}. "
            f"❌ FAIL — "
            f"{name}"
        )

        print(
            f"    {error}"
        )

        return False


# ============================================================
# 1
# ============================================================

def test_structured_required_section():

    content = """
    <h3>Requirements</h3>
    <ul>
        <li>Experience with Python</li>
        <li>Experience with Docker</li>
        <li>Strong knowledge of AWS</li>
    </ul>
    """

    result = (
        extract_requirements(
            content
        )
    )

    required = (
        result[
            "required_skills"
        ]
    )

    assert_contains(
        required,
        "Python",
        "Python should be required",
    )

    assert_contains(
        required,
        "Docker",
        "Docker should be required",
    )

    assert_contains(
        required,
        "AWS",
        "AWS should be required",
    )


# ============================================================
# 2
# ============================================================

def test_preferred_section():

    content = """
    <h3>Preferred Qualifications</h3>
    <ul>
        <li>Experience with Kubernetes</li>
        <li>Knowledge of Terraform</li>
    </ul>
    """

    result = (
        extract_requirements(
            content
        )
    )

    preferred = (
        result[
            "preferred_skills"
        ]
    )

    assert_contains(
        preferred,
        "Kubernetes",
        "Kubernetes should be preferred",
    )

    assert_contains(
        preferred,
        "Terraform",
        "Terraform should be preferred",
    )


# ============================================================
# 3
# ============================================================

def test_inline_required_heading():

    content = """
    <p>
        What you'll need: Experience with Python and AWS.
    </p>
    """

    result = (
        extract_requirements(
            content
        )
    )

    required = (
        result[
            "required_skills"
        ]
    )

    assert_contains(
        required,
        "Python",
        "Python should be required",
    )

    assert_contains(
        required,
        "AWS",
        "AWS should be required",
    )


# ============================================================
# 4
# ============================================================

def test_wrapped_requirement():

    content = """
    <p>
        You must have hands-on experience with Docker
        and Kubernetes.
    </p>
    """

    result = (
        extract_requirements(
            content
        )
    )

    required = (
        result[
            "required_skills"
        ]
    )

    assert_contains(
        required,
        "Docker",
        "Docker should be required",
    )

    assert_contains(
        required,
        "Kubernetes",
        "Wrapped Kubernetes should remain required",
    )


# ============================================================
# 5
# ============================================================

def test_responsibilities_remain_general():

    content = """
    <h3>What You'll Do</h3>
    <p>
        Build services using Python and AWS.
    </p>
    """

    result = (
        extract_requirements(
            content
        )
    )

    assert_contains(
        result[
            "general_skills"
        ],
        "Python",
        "Python should remain general",
    )

    assert_not_contains(
        result[
            "required_skills"
        ],
        "Python",
        "Responsibility should not become required",
    )


# ============================================================
# 6
# ============================================================

def test_go_false_positive():

    skills = (
        extract_skills(
            (
                "Help the product go to market "
                "and go beyond customer expectations."
            )
        )
    )

    assert_not_contains(
        skills,
        "Go",
        "Normal English go must not mean Golang",
    )


# ============================================================
# 7
# ============================================================

def test_java_or_go():

    content = """
    <p>
        Experience with Java or Go.
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
                "Java",
                "Go",
            },
        )
    )

    assert_equal(
        group[
            "min_matches"
        ],
        1,
        "Java OR Go should require one match",
    )


# ============================================================
# 8
# ============================================================

def test_preferred_payment_methods_false_positive():

    content = """
    <p>
        Our wallet supports preferred payment methods
        and uses the highest security mechanisms.
    </p>
    """

    result = (
        extract_requirements(
            content
        )
    )

    assert_not_contains(
        result[
            "preferred_skills"
        ],
        "Security",
        (
            "Preferred payment methods must not "
            "make Security preferred"
        ),
    )


# ============================================================
# 9
# ============================================================

def test_specific_aws_preferred():

    content = """
    <p>
        Extensive experience in software development
        and a deep understanding of distributed systems
        and public cloud platforms (AWS preferred).
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
            "Distributed Systems should stay required"
        ),
    )

    assert_contains(
        result[
            "preferred_skills"
        ],
        "AWS",
        (
            "Only AWS should become preferred"
        ),
    )


# ============================================================
# 10
# ============================================================

def test_figma_example_groups():

    content = """
    <p>
        Strong proficiency in modern front-end frameworks
        (e.g., React/TypeScript) and back-end technologies
        (e.g., Ruby, Python, Go, C++, PostgreSQL).
    </p>
    """

    result = (
        extract_requirements(
            content
        )
    )

    frontend_group = (
        find_group(
            result,
            {
                "React",
                "TypeScript",
            },
        )
    )

    backend_group = (
        find_group(
            result,
            {
                "Ruby",
                "Python",
                "Go",
                "C++",
                "PostgreSQL",
            },
        )
    )

    assert_equal(
        frontend_group[
            "min_matches"
        ],
        1,
        "Frontend example group should require one",
    )

    assert_equal(
        backend_group[
            "min_matches"
        ],
        1,
        "Backend example group should require one",
    )

    # These examples must NOT become seven separate
    # mandatory skills.

    assert_equal(
        result[
            "required_skills"
        ],
        [],
        (
            "Example technologies should be represented "
            "through groups rather than standalone requirements"
        ),
    )


# ============================================================
# 11
# ============================================================

def test_cloud_provider_group():

    content = """
    <p>
        Experience with major cloud providers
        (AWS, Azure, GCP).
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
                "AWS",
                "Azure",
                "GCP",
            },
        )
    )

    assert_equal(
        group[
            "min_matches"
        ],
        1,
        (
            "Cloud provider examples should require "
            "one matching provider"
        ),
    )


# ============================================================
# 12
# ============================================================

def test_mixed_or_and_logic():

    content = """
    <p>
        Proficient in Python or Javascript/Typescript,
        and SQL.
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
        "SQL",
        "SQL must remain independently required",
    )

    group = (
        find_group(
            result,
            {
                "Python",
                "JavaScript",
                "TypeScript",
            },
        )
    )

    assert_equal(
        group[
            "min_matches"
        ],
        1,
        (
            "Python/JavaScript/TypeScript "
            "should require one"
        ),
    )


# ============================================================
# 13
# ============================================================

def test_at_least_two_of():

    content = """
    <h3>Minimum Requirements</h3>
    <p>
        Proficiency in at least two of:
        Ruby, Node.js, Python, or Next.js
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
                "Ruby",
                "Node.js",
                "Python",
                "Next.js",
            },
        )
    )

    assert_equal(
        group[
            "min_matches"
        ],
        2,
        (
            "'at least two of' must require two matches"
        ),
    )


# ============================================================
# 14
# ============================================================

def test_inline_framework_examples():

    content = """
    <h3>Minimum Requirements</h3>
    <p>
        Proficiency in Python and common data and ML
        frameworks like SQL, Spark, and PyTorch.
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
        "Python",
        (
            "Python should remain independently required"
        ),
    )

    group = (
        find_group(
            result,
            {
                "SQL",
                "Spark",
                "PyTorch",
            },
        )
    )

    assert_equal(
        group[
            "min_matches"
        ],
        1,
        "Framework examples should require one match",
    )


# ============================================================
# 15
# ============================================================

def test_single_known_example_not_required():

    content = """
    <p>
        Experience with orchestration platforms,
        such as Temporal and AWS Step Functions.
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
        "AWS",
        (
            "AWS is an example here, not a mandatory skill"
        ),
    )

    assert_contains(
        result[
            "general_skills"
        ],
        "AWS",
        (
            "AWS example should still be retained "
            "as general evidence"
        ),
    )


# ============================================================
# 16
# ============================================================

def test_minimum_count_matcher_success():

    groups = [
        {
            "section": (
                "required"
            ),

            "skills": [
                "Ruby",
                "Node.js",
                "Python",
                "Next.js",
            ],

            "min_matches": 2,

            "kind": (
                "minimum_count"
            ),

            "text": (
                "At least two"
            ),
        }
    ]

    (
        score,
        _,
        _,
        group_results,
    ) = calculate_requirement_score(
        [],
        groups,
        {
            "Python",
            "Ruby",
        },
        "required",
    )

    assert_equal(
        score,
        100.0,
        (
            "Two matching technologies should satisfy "
            "a min_matches=2 group"
        ),
    )

    assert_equal(
        group_results[
            0
        ][
            "matched_count"
        ],
        2,
        "Matched count should be two",
    )


# ============================================================
# 17
# ============================================================

def test_minimum_count_matcher_failure():

    groups = [
        {
            "section": (
                "required"
            ),

            "skills": [
                "Ruby",
                "Node.js",
                "Python",
                "Next.js",
            ],

            "min_matches": 2,

            "kind": (
                "minimum_count"
            ),

            "text": (
                "At least two"
            ),
        }
    ]

    (
        score,
        _,
        _,
        _,
    ) = calculate_requirement_score(
        [],
        groups,
        {
            "Python",
        },
        "required",
    )

    assert_equal(
        score,
        0.0,
        (
            "One matching technology must not satisfy "
            "a min_matches=2 group"
        ),
    )


# ============================================================
# 18
# ============================================================

def test_sql_and_language_group_scoring():

    groups = [
        {
            "section": (
                "required"
            ),

            "skills": [
                "Python",
                "JavaScript",
                "TypeScript",
            ],

            "min_matches": 1,

            "kind": (
                "alternative"
            ),

            "text": (
                "Python or JS/TS and SQL"
            ),
        }
    ]

    (
        partial_score,
        _,
        _,
        _,
    ) = calculate_requirement_score(
        [
            "SQL"
        ],
        groups,
        {
            "SQL"
        },
        "required",
    )

    assert_equal(
        partial_score,
        50.0,
        (
            "SQL alone should satisfy only one "
            "of two requirement units"
        ),
    )

    (
        full_score,
        _,
        _,
        _,
    ) = calculate_requirement_score(
        [
            "SQL"
        ],
        groups,
        {
            "SQL",
            "Python",
        },
        "required",
    )

    assert_equal(
        full_score,
        100.0,
        (
            "SQL plus one language should satisfy "
            "both requirement units"
        ),
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 90)

    print(
        "REQUIREMENT EXTRACTOR V3 TEST"
    )

    print("=" * 90)
    print()

    tests = [
        (
            "Structured required section",
            test_structured_required_section,
        ),
        (
            "Preferred section",
            test_preferred_section,
        ),
        (
            "Inline required heading",
            test_inline_required_heading,
        ),
        (
            "Wrapped requirement continuation",
            test_wrapped_requirement,
        ),
        (
            "Responsibilities remain general",
            test_responsibilities_remain_general,
        ),
        (
            "Go false-positive prevention",
            test_go_false_positive,
        ),
        (
            "Java OR Go",
            test_java_or_go,
        ),
        (
            "Preferred payment methods false positive",
            test_preferred_payment_methods_false_positive,
        ),
        (
            "Specific AWS preferred",
            test_specific_aws_preferred,
        ),
        (
            "Figma example groups",
            test_figma_example_groups,
        ),
        (
            "Cloud provider group",
            test_cloud_provider_group,
        ),
        (
            "Mixed OR + AND logic",
            test_mixed_or_and_logic,
        ),
        (
            "At least two of",
            test_at_least_two_of,
        ),
        (
            "Inline framework examples",
            test_inline_framework_examples,
        ),
        (
            "Single known example is not required",
            test_single_known_example_not_required,
        ),
        (
            "Matcher min-count success",
            test_minimum_count_matcher_success,
        ),
        (
            "Matcher min-count failure",
            test_minimum_count_matcher_failure,
        ),
        (
            "SQL + language-group scoring",
            test_sql_and_language_group_scoring,
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
        f"Passed: "
        f"{passed}/{len(tests)}"
    )

    print(
        f"Failed: "
        f"{failed}/{len(tests)}"
    )

    print()

    if failed == 0:

        print(
            "✅ REQUIREMENT EXTRACTOR V3 TEST PASSED"
        )

    else:

        print(
            "❌ REQUIREMENT EXTRACTOR V3 NEEDS ADJUSTMENT"
        )

    print("=" * 90)


if __name__ == "__main__":

    main()
