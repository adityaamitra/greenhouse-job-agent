from src.matching.matcher import (
    MANUAL_PRIORITY_THRESHOLD,
    MANUAL_MIN_CONFIDENCE,
    calculate_dynamic_weighted_score,
    calculate_job_fit_score,
    calculate_resume_selection_score,
    get_route,
)


def assert_close(
    actual,
    expected,
    message,
    tolerance=0.02,
):

    if abs(
        actual
        - expected
    ) > tolerance:

        raise AssertionError(
            f"{message}: "
            f"expected {expected:.2f}, "
            f"got {actual:.2f}"
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


# ============================================================
# TEST 1
# ============================================================

def test_missing_components_are_excluded():

    result = (
        calculate_job_fit_score(
            required_score=100.0,
            preferred_score=100.0,
            semantic_score=60.0,
            experience_score=100.0,

            required_available=False,
            preferred_available=False,
            experience_available=False,
        )
    )

    assert_close(
        result[
            "score"
        ],
        60.0,
        (
            "Semantic-only evidence should preserve "
            "the semantic score"
        ),
    )

    assert_close(
        result[
            "confidence"
        ],
        30.0,
        (
            "Semantic-only evidence should have "
            "30% confidence"
        ),
    )


# ============================================================
# TEST 2
# ============================================================

def test_required_plus_semantic_normalization():

    result = (
        calculate_job_fit_score(
            required_score=100.0,
            preferred_score=100.0,
            semantic_score=75.0,
            experience_score=100.0,

            required_available=True,
            preferred_available=False,
            experience_available=False,
        )
    )

    # (100*45 + 75*30) / 75
    expected = (
        90.0
    )

    assert_close(
        result[
            "score"
        ],
        expected,
        (
            "Required + semantic should normalize "
            "over active weight"
        ),
    )

    assert_close(
        result[
            "confidence"
        ],
        75.0,
        (
            "Required + semantic should produce "
            "75% confidence"
        ),
    )

    route = (
        get_route(
            result[
                "score"
            ],
            result[
                "confidence"
            ],
            True,
        )
    )

    assert_equal(
        route,
        "MANUAL_PRIORITY",
        (
            "Strong required + semantic evidence "
            "should qualify for Manual Priority"
        ),
    )


# ============================================================
# TEST 3
# ============================================================

def test_scale_gen_ai_pattern():

    result = (
        calculate_job_fit_score(
            required_score=100.0,
            preferred_score=100.0,
            semantic_score=66.20,
            experience_score=100.0,

            required_available=True,
            preferred_available=False,
            experience_available=True,
        )
    )

    assert_close(
        result[
            "score"
        ],
        88.73,
        (
            "Scale Gen AI calibration score "
            "should remain 88.73"
        ),
    )

    assert_close(
        result[
            "confidence"
        ],
        90.0,
        (
            "Scale Gen AI confidence "
            "should remain 90%"
        ),
    )

    assert_equal(
        get_route(
            result[
                "score"
            ],
            result[
                "confidence"
            ],
            True,
        ),
        "MANUAL_PRIORITY",
        (
            "Scale Gen AI calibration pattern "
            "should be Manual Priority"
        ),
    )


# ============================================================
# TEST 4
# ============================================================

def test_stripe_ai_pattern():

    result = (
        calculate_job_fit_score(
            required_score=66.67,
            preferred_score=100.0,
            semantic_score=90.20,
            experience_score=65.0,

            required_available=True,
            preferred_available=False,
            experience_available=True,
        )
    )

    assert_close(
        result[
            "score"
        ],
        74.23,
        (
            "Stripe AI calibration score "
            "should remain around 74.23"
        ),
    )

    assert_equal(
        get_route(
            result[
                "score"
            ],
            result[
                "confidence"
            ],
            True,
        ),
        "AGENT_APPLY",
        (
            "Strong semantics should not override "
            "requirement and experience gaps"
        ),
    )


# ============================================================
# TEST 5
# ============================================================

def test_high_fit_low_confidence_is_not_manual():

    result = (
        calculate_job_fit_score(
            required_score=100.0,
            preferred_score=100.0,
            semantic_score=90.0,
            experience_score=100.0,

            required_available=False,
            preferred_available=False,
            experience_available=False,
        )
    )

    assert_close(
        result[
            "score"
        ],
        90.0,
        (
            "Semantic-only fit should still represent "
            "the semantic evidence"
        ),
    )

    assert_close(
        result[
            "confidence"
        ],
        30.0,
        (
            "Semantic-only fit should remain "
            "low confidence"
        ),
    )

    assert_equal(
        get_route(
            result[
                "score"
            ],
            result[
                "confidence"
            ],
            False,
        ),
        "AGENT_APPLY",
        (
            "High fit without required evidence "
            "must not become Manual Priority"
        ),
    )


# ============================================================
# TEST 6
# ============================================================

def test_resume_selection_without_required_evidence():

    score = (
        calculate_resume_selection_score(
            role_score=100.0,
            semantic_score=60.0,
            required_score=100.0,
            required_available=False,
        )
    )

    # (100*55 + 60*25) / 80
    expected = (
        87.50
    )

    assert_close(
        score,
        expected,
        (
            "Missing required extraction should "
            "be excluded from resume selection"
        ),
    )


# ============================================================
# TEST 7
# ============================================================

def test_resume_selection_with_required_evidence():

    score = (
        calculate_resume_selection_score(
            role_score=100.0,
            semantic_score=60.0,
            required_score=100.0,
            required_available=True,
        )
    )

    # 100*.55 + 60*.25 + 100*.20
    expected = (
        90.0
    )

    assert_close(
        score,
        expected,
        (
            "Resume selection should use all "
            "three available components"
        ),
    )


# ============================================================
# TEST 8
# ============================================================

def test_route_threshold_boundary():

    assert_equal(
        get_route(
            MANUAL_PRIORITY_THRESHOLD,
            MANUAL_MIN_CONFIDENCE,
            True,
        ),
        "MANUAL_PRIORITY",
        (
            "Exact score/confidence threshold "
            "should qualify"
        ),
    )

    assert_equal(
        get_route(
            MANUAL_PRIORITY_THRESHOLD
            - 0.01,
            100.0,
            True,
        ),
        "AGENT_APPLY",
        (
            "Score below threshold should not qualify"
        ),
    )

    assert_equal(
        get_route(
            100.0,
            MANUAL_MIN_CONFIDENCE
            - 0.01,
            True,
        ),
        "AGENT_APPLY",
        (
            "Confidence below threshold should not qualify"
        ),
    )

    assert_equal(
        get_route(
            100.0,
            100.0,
            False,
        ),
        "AGENT_APPLY",
        (
            "Missing required evidence should not qualify"
        ),
    )


# ============================================================
# RUNNER
# ============================================================

def run_test(
    number,
    name,
    function,
):

    try:

        function()

        print(
            f"{number:02}. "
            f"✅ PASS — "
            f"{name}"
        )

        return (
            True
        )

    except Exception as error:

        print(
            f"{number:02}. "
            f"❌ FAIL — "
            f"{name}"
        )

        print(
            f"    {error}"
        )

        return (
            False
        )


def main():

    print()
    print(
        "=" * 90
    )

    print(
        "MATCHER SCORE CALIBRATION V2.1 TEST"
    )

    print(
        "=" * 90
    )

    print()

    tests = [
        (
            "Missing components are excluded",
            test_missing_components_are_excluded,
        ),

        (
            "Required + semantic normalization",
            test_required_plus_semantic_normalization,
        ),

        (
            "Scale Gen AI calibration pattern",
            test_scale_gen_ai_pattern,
        ),

        (
            "Stripe AI calibration pattern",
            test_stripe_ai_pattern,
        ),

        (
            "High fit / low confidence gate",
            test_high_fit_low_confidence_is_not_manual,
        ),

        (
            "Resume selection without requirements",
            test_resume_selection_without_required_evidence,
        ),

        (
            "Resume selection with requirements",
            test_resume_selection_with_required_evidence,
        ),

        (
            "Manual route threshold boundaries",
            test_route_threshold_boundary,
        ),
    ]

    passed = (
        0
    )

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

            passed += (
                1
            )

    failed = (
        len(
            tests
        )
        - passed
    )

    print()
    print(
        "=" * 90
    )

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
            "✅ MATCHER SCORE CALIBRATION V2.1 TEST PASSED"
        )

    else:

        print(
            "❌ MATCHER SCORE CALIBRATION V2.1 NEEDS ADJUSTMENT"
        )

    print(
        "=" * 90
    )


if __name__ == "__main__":

    main()
