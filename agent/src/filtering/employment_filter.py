import re


# ============================================================
# DEFINITELY NON-FULL-TIME TITLE PATTERNS
# ============================================================

EXCLUDED_TITLE_PATTERNS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\bco[\s-]?op\b",
    r"\bpart[\s-]?time\b",
    r"\bcontractor\b",
    r"\btemporary\b",
    r"\btemp\b",
    r"\bseasonal\b",
    r"\bfellowship\b",
    r"\bfellow\b",
    r"\bapprentice\b",
    r"\bapprenticeship\b",
]


# ============================================================
# CONTRACT EMPLOYMENT PATTERNS
#
# We intentionally do NOT use a generic:
#
#     r"\bcontract\b"
#
# because titles such as:
#
#     Software Engineer - Smart Contract, Bridge
#
# refer to blockchain technology, not employment type.
# ============================================================

CONTRACT_EMPLOYMENT_PATTERNS = [
    # Software Engineer - Contract
    r"(?:-|–|—|\()\s*contract\s*\)?$",

    # Software Engineer (Contract)
    r"\(\s*contract\s*\)",

    # Contract Software Engineer
    r"^\s*contract\s+",

    # Software Engineer, Contract
    r",\s*contract\s*$",

    # Software Engineer - 6 Month Contract
    r"\b\d+\s*(?:month|months|mo)\s+contract\b",

    # Software Engineer - Contract Role
    r"\bcontract\s+(?:role|position|opportunity)\b",

    # Software Engineer - Fixed Term
    r"\bfixed[\s-]?term\b",
]


# ============================================================
# STRUCTURED EMPLOYMENT VALUES
# ============================================================

FULL_TIME_VALUES = {
    "full time",
    "full-time",
    "fulltime",
    "regular",
    "regular full time",
    "regular full-time",
    "permanent",
}


NON_FULL_TIME_VALUES = {
    "intern",
    "internship",
    "co-op",
    "coop",
    "part time",
    "part-time",
    "parttime",
    "contract",
    "contractor",
    "temporary",
    "temp",
    "seasonal",
    "fellowship",
    "apprenticeship",
    "fixed term",
    "fixed-term",
}


def normalize_text(
    value,
) -> str:
    """
    Normalize a value for comparison.
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


def is_smart_contract_title(
    title: str,
) -> bool:
    """
    Protect blockchain / smart-contract engineering titles.

    Examples that should NOT be treated as contract employment:

        Software Engineer - Smart Contract, Bridge
        Smart Contract Engineer
        Blockchain / Smart Contract Developer
    """

    normalized = normalize_text(
        title
    )

    smart_contract_patterns = [
        r"\bsmart[\s-]?contract\b",
        r"\bsmart[\s-]?contracts\b",
    ]

    return any(
        re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        )
        for pattern in smart_contract_patterns
    )


def title_has_excluded_type(
    title: str,
) -> tuple[bool, str | None]:
    """
    Detect obvious non-full-time employment types
    from the job title.
    """

    normalized_title = normalize_text(
        title
    )

    # --------------------------------------------------------
    # INTERN / CO-OP / PART-TIME / TEMP ETC.
    # --------------------------------------------------------

    for pattern in EXCLUDED_TITLE_PATTERNS:

        match = re.search(
            pattern,
            normalized_title,
            flags=re.IGNORECASE,
        )

        if match:

            return (
                True,
                match.group(0),
            )

    # --------------------------------------------------------
    # CONTRACT EMPLOYMENT
    #
    # Smart-contract titles must not be rejected merely
    # because they contain the word "contract".
    # --------------------------------------------------------

    if not is_smart_contract_title(
        normalized_title
    ):

        for pattern in CONTRACT_EMPLOYMENT_PATTERNS:

            match = re.search(
                pattern,
                normalized_title,
                flags=re.IGNORECASE,
            )

            if match:

                return (
                    True,
                    match.group(0),
                )

    return (
        False,
        None,
    )


def extract_metadata_values(
    job: dict,
) -> list[tuple[str, str]]:
    """
    Extract employment-related metadata from Greenhouse.

    Example:

        [
            {
                "name": "Employment Type",
                "value": "Full Time"
            }
        ]
    """

    results = []

    metadata = job.get(
        "metadata",
        [],
    )

    if not isinstance(
        metadata,
        list,
    ):
        return results

    for item in metadata:

        if not isinstance(
            item,
            dict,
        ):
            continue

        name = normalize_text(
            item.get("name")
        )

        value = item.get(
            "value"
        )

        if isinstance(
            value,
            list,
        ):

            for list_value in value:

                normalized_value = normalize_text(
                    list_value
                )

                if normalized_value:

                    results.append(
                        (
                            name,
                            normalized_value,
                        )
                    )

        else:

            normalized_value = normalize_text(
                value
            )

            if normalized_value:

                results.append(
                    (
                        name,
                        normalized_value,
                    )
                )

    return results


def inspect_structured_employment_type(
    job: dict,
) -> tuple[str, str | None]:
    """
    Examine structured Greenhouse metadata.

    Returns:

        ("FULL_TIME", evidence)
        ("NON_FULL_TIME", evidence)
        ("UNKNOWN", None)
    """

    metadata_values = extract_metadata_values(
        job
    )

    employment_field_names = {
        "employment type",
        "employment",
        "job type",
        "worker type",
        "position type",
        "time type",
    }

    for (
        field_name,
        value,
    ) in metadata_values:

        if (
            field_name
            not in employment_field_names
        ):
            continue

        normalized = (
            value
            .replace("_", " ")
            .strip()
        )

        if (
            normalized
            in FULL_TIME_VALUES
        ):

            return (
                "FULL_TIME",
                f"{field_name}: {value}",
            )

        if (
            normalized
            in NON_FULL_TIME_VALUES
        ):

            return (
                "NON_FULL_TIME",
                f"{field_name}: {value}",
            )

    return (
        "UNKNOWN",
        None,
    )


def classify_employment_type(
    job: dict,
) -> dict:
    """
    Decide whether a Greenhouse job should proceed.

    V1 policy:

    1. Explicit internship/co-op/part-time/etc. title
       -> REJECT

    2. Explicit contract-employment title
       -> REJECT

    3. "Smart Contract" technical title
       -> NOT rejected merely because it contains "contract"

    4. Structured metadata says non-full-time
       -> REJECT

    5. Structured metadata says full-time
       -> ACCEPT

    6. Employment type unavailable
       -> ACCEPT_UNKNOWN
    """

    title = job.get(
        "title",
        "",
    )

    (
        excluded_from_title,
        title_evidence,
    ) = title_has_excluded_type(
        title
    )

    if excluded_from_title:

        return {
            "decision": "REJECT",

            "employment_type": (
                "NON_FULL_TIME"
            ),

            "reason": (
                "Excluded employment type "
                "detected in title"
            ),

            "evidence": (
                title_evidence
            ),
        }

    (
        structured_status,
        structured_evidence,
    ) = inspect_structured_employment_type(
        job
    )

    if (
        structured_status
        == "NON_FULL_TIME"
    ):

        return {
            "decision": "REJECT",

            "employment_type": (
                "NON_FULL_TIME"
            ),

            "reason": (
                "Structured employment metadata "
                "indicates non-full-time role"
            ),

            "evidence": (
                structured_evidence
            ),
        }

    if (
        structured_status
        == "FULL_TIME"
    ):

        return {
            "decision": "ACCEPT",

            "employment_type": (
                "FULL_TIME"
            ),

            "reason": (
                "Structured employment metadata "
                "indicates full-time role"
            ),

            "evidence": (
                structured_evidence
            ),
        }

    return {
        "decision": (
            "ACCEPT_UNKNOWN"
        ),

        "employment_type": (
            "UNKNOWN"
        ),

        "reason": (
            "No explicit non-full-time "
            "employment type detected"
        ),

        "evidence": None,
    }


def filter_by_employment_type(
    jobs: list[dict],
) -> tuple[
    list[dict],
    list[dict],
]:
    """
    Split jobs into:

        accepted_jobs
        rejected_jobs
    """

    accepted_jobs = []

    rejected_jobs = []

    for job in jobs:

        classification = (
            classify_employment_type(
                job
            )
        )

        if (
            classification[
                "decision"
            ]
            == "REJECT"
        ):

            rejected_jobs.append(
                {
                    "job": job,

                    "classification": (
                        classification
                    ),
                }
            )

        else:

            accepted_jobs.append(
                job
            )

    return (
        accepted_jobs,
        rejected_jobs,
    )
