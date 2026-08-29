from src.database.repository import (
    find_stale_job_rows,
    normalize_greenhouse_job_ids,
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


def stale_ids(
    rows,
):

    return [
        row[
            "greenhouse_job_id"
        ]
        for row
        in rows
    ]


def test_normalization():

    result = (
        normalize_greenhouse_job_ids(
            [
                123,
                "456",
                " 789 ",
                None,
                "",
            ]
        )
    )

    assert_equal(
        result,
        {
            "123",
            "456",
            "789",
        },
        "Job IDs should normalize to strings",
    )


def test_missing_job_becomes_stale():

    tracked = [
        {
            "greenhouse_job_id": "1",
            "is_active": True,
        },
        {
            "greenhouse_job_id": "2",
            "is_active": True,
        },
        {
            "greenhouse_job_id": "3",
            "is_active": True,
        },
    ]

    stale = (
        find_stale_job_rows(
            tracked,
            [
                "1",
                "3",
            ],
        )
    )

    assert_equal(
        stale_ids(
            stale
        ),
        [
            "2"
        ],
        "Missing tracked job should become stale",
    )


def test_live_job_stays_active():

    tracked = [
        {
            "greenhouse_job_id": "900",
            "is_active": True,
        }
    ]

    stale = (
        find_stale_job_rows(
            tracked,
            [
                900
            ],
        )
    )

    assert_equal(
        stale,
        [],
        "Live job should not be marked stale",
    )


def test_already_inactive_is_ignored():

    tracked = [
        {
            "greenhouse_job_id": "10",
            "is_active": False,
        },
        {
            "greenhouse_job_id": "11",
            "is_active": True,
        },
    ]

    stale = (
        find_stale_job_rows(
            tracked,
            [
                "99"
            ],
        )
    )

    assert_equal(
        stale_ids(
            stale
        ),
        [
            "11"
        ],
        "Already inactive rows should not be reprocessed",
    )


def test_empty_live_set_is_safe():

    tracked = [
        {
            "greenhouse_job_id": "1",
            "is_active": True,
        },
        {
            "greenhouse_job_id": "2",
            "is_active": True,
        },
    ]

    stale = (
        find_stale_job_rows(
            tracked,
            [],
        )
    )

    assert_equal(
        stale,
        [],
        (
            "Empty board response must never mass-deactivate "
            "tracked jobs"
        ),
    )


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


def main():

    print()
    print(
        "=" * 90
    )
    print(
        "JOB LIFECYCLE V1 TEST"
    )
    print(
        "=" * 90
    )
    print()

    tests = [
        (
            "Greenhouse ID normalization",
            test_normalization,
        ),
        (
            "Missing job becomes stale",
            test_missing_job_becomes_stale,
        ),
        (
            "Live job stays active",
            test_live_job_stays_active,
        ),
        (
            "Already inactive row ignored",
            test_already_inactive_is_ignored,
        ),
        (
            "Empty board response safety guard",
            test_empty_live_set_is_safe,
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
    print(
        "=" * 90
    )
    print(
        f"Passed: {passed}/{len(tests)}"
    )
    print(
        f"Failed: {failed}/{len(tests)}"
    )
    print()

    if failed == 0:

        print(
            "✅ JOB LIFECYCLE V1 TEST PASSED"
        )

    else:

        print(
            "❌ JOB LIFECYCLE V1 NEEDS ADJUSTMENT"
        )

    print(
        "=" * 90
    )


if __name__ == "__main__":

    main()

