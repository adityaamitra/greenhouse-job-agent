import re


# ============================================================
# ELIGIBILITY GATE
# ============================================================
#
# This gate is deliberately conservative.
#
# It DOES NOT guess whether the applicant satisfies
# citizenship, clearance, export-control, sponsorship,
# certification, or licensing requirements.
#
# If one of those requirements is detected:
#
#     NEEDS_ASSISTANCE
#
# rather than silently applying or automatically rejecting.
#
# ============================================================


# ============================================================
# HELPERS
# ============================================================

def normalize_text(
    text: str,
) -> str:
    """
    Normalize job title / job description text
    before eligibility matching.
    """

    if not text:
        return ""

    # Remove basic HTML tags.
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # Basic HTML entity cleanup.
    text = (
        text
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
    )

    # Collapse whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return (
        text
        .strip()
        .lower()
    )


def extract_context(
    text: str,
    match_start: int,
    match_end: int,
    window: int = 120,
) -> str:
    """
    Return a short snippet around a detected
    eligibility requirement.
    """

    start = max(
        0,
        match_start - window,
    )

    end = min(
        len(text),
        match_end + window,
    )

    return (
        text[
            start:end
        ]
        .strip()
    )


def has_exception(
    text: str,
    patterns: list[str],
) -> bool:
    """
    Return True when a known exception is present.

    Example:

        "No security clearance required"

    should NOT trigger a clearance warning.
    """

    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


# ============================================================
# CLEARANCE EXCEPTIONS
# ============================================================

CLEARANCE_EXCEPTIONS = [
    r"\bno\s+(?:security\s+)?clearance\s+(?:is\s+)?required\b",

    r"\bsecurity\s+clearance\s+not\s+required\b",

    r"\bdoes\s+not\s+require\s+(?:a\s+)?security\s+clearance\b",
]


# ============================================================
# CITIZENSHIP EXCEPTIONS
# ============================================================

CITIZENSHIP_EXCEPTIONS = [
    r"\bcitizenship\s+(?:is\s+)?not\s+required\b",

    r"\bregardless\s+of\s+citizenship\b",

    r"\bdo\s+not\s+require\s+u\.?s\.?\s+citizenship\b",
]


# ============================================================
# SECURITY CLEARANCE
# ============================================================

CLEARANCE_PATTERNS = [
    # --------------------------------------------------------
    # Active / current clearance
    # --------------------------------------------------------

    r"\bactive\s+(?:secret|top\s+secret|ts\/sci|security)\s+clearance\b",

    r"\bcurrent\s+(?:secret|top\s+secret|ts\/sci|security)\s+clearance\b",

    # --------------------------------------------------------
    # Explicit required clearance
    # --------------------------------------------------------

    r"\b(?:secret|top\s+secret|ts\/sci)\s+clearance\s+(?:is\s+)?required\b",

    r"\bsecurity\s+clearance\s+(?:is\s+)?required\b",

    # --------------------------------------------------------
    # Must have / hold / possess
    # --------------------------------------------------------

    r"\bmust\s+(?:have|hold|possess|maintain)\b.{0,80}\bclearance\b",

    # --------------------------------------------------------
    # Requires clearance
    # --------------------------------------------------------

    r"\brequires?\b.{0,80}\b(?:secret|top\s+secret|ts\/sci|security)\s+clearance\b",

    # --------------------------------------------------------
    # Eligibility to obtain clearance
    # --------------------------------------------------------

    r"\beligible\s+to\s+(?:obtain|receive)\b.{0,80}\bclearance\b",

    r"\bability\s+to\s+obtain\b.{0,80}\bclearance\b",
]


# ============================================================
# CITIZENSHIP
# ============================================================

CITIZENSHIP_PATTERNS = [
    r"\bu\.?s\.?\s+citizenship\s+(?:is\s+)?required\b",

    r"\bus\s+citizenship\s+(?:is\s+)?required\b",

    r"\bmust\s+be\s+(?:a\s+)?u\.?s\.?\s+citizen\b",

    r"\bmust\s+be\s+(?:a\s+)?us\s+citizen\b",

    r"\bonly\s+u\.?s\.?\s+citizens\b",

    r"\bu\.?s\.?\s+citizens\s+only\b",

    r"\bcandidates?\s+must\s+(?:be|hold)\b.{0,50}\bcitizenship\b",
]


# ============================================================
# EXPORT CONTROL
# ============================================================

EXPORT_CONTROL_PATTERNS = [
    # ITAR
    r"\bitar\b",

    r"\binternational\s+traffic\s+in\s+arms\s+regulations\b",

    # General export-control language
    r"\bexport\s+control(?:led)?\b",

    r"\bexport\s+compliance\b",

    # U.S. person requirements
    r"\bu\.?s\.?\s+person\s+(?:status\s+)?required\b",

    r"\bmust\s+qualify\s+as\s+(?:a\s+)?u\.?s\.?\s+person\b",

    # Export Administration Regulations
    r"\bear\s+regulated\b",
]


# ============================================================
# SPONSORSHIP RESTRICTIONS
# ============================================================

SPONSORSHIP_PATTERNS = [
    # --------------------------------------------------------
    # Simple sponsorship denial
    # --------------------------------------------------------

    r"\bno\s+(?:visa\s+)?sponsorship\b",

    r"\bvisa\s+sponsorship\s+(?:is\s+)?not\s+available\b",

    r"\bsponsorship\s+(?:is\s+)?not\s+available\b",

    # --------------------------------------------------------
    # We do / will not sponsor
    # --------------------------------------------------------

    r"\bwe\s+(?:do|will)\s+not\s+sponsor\b",

    r"\bwe\s+(?:do|will)\s+not\s+provide\b.{0,40}\bsponsorship\b",

    # --------------------------------------------------------
    # Cannot sponsor
    # --------------------------------------------------------

    r"\bcannot\s+sponsor\b",

    r"\bcan't\s+sponsor\b",

    r"\bcannot\s+provide\b.{0,40}\bsponsorship\b",

    # --------------------------------------------------------
    # Unable to sponsor
    # --------------------------------------------------------

    r"\bunable\s+to\s+sponsor\b",

    r"\bunable\s+to\s+provide\b.{0,40}\bsponsorship\b",

    # Handles:
    #
    # "We are unable to provide visa sponsorship..."
    #
    r"\bunable\s+to\s+provide\s+(?:visa\s+)?sponsorship\b",

    # --------------------------------------------------------
    # Not able to sponsor
    # --------------------------------------------------------

    r"\bnot\s+able\s+to\s+sponsor\b",

    r"\bnot\s+able\s+to\s+provide\b.{0,40}\bsponsorship\b",

    # --------------------------------------------------------
    # Will not provide sponsorship
    # --------------------------------------------------------

    r"\bwill\s+not\s+provide\s+(?:visa\s+)?sponsorship\b",

    # --------------------------------------------------------
    # Candidate cannot require sponsorship
    # --------------------------------------------------------

    r"\bwithout\s+(?:current\s+or\s+future\s+)?sponsorship\b",

    r"\bwithout\s+requiring\s+sponsorship\b",

    r"\bmust\s+not\s+require\s+sponsorship\b",

    r"\bdo\s+not\s+require\s+sponsorship\s+now\s+or\s+in\s+the\s+future\b",

    r"\bmust\s+be\s+authorized\b.{0,80}\bwithout\s+sponsorship\b",

    # --------------------------------------------------------
    # Future sponsorship restrictions
    # --------------------------------------------------------

    r"\bwill\s+not\s+sponsor\b.{0,80}\b(?:now|future|future employment)\b",

    r"\bno\s+sponsorship\b.{0,80}\b(?:now|future)\b",
]


# ============================================================
# REQUIRED LICENSES / CERTIFICATIONS
# ============================================================

LICENSE_CERT_PATTERNS = [
    r"\b(?:must|required\s+to)\s+(?:have|hold|possess|maintain)\b.{0,80}\b(?:license|licence|certification)\b",

    r"\b(?:active|current|valid)\b.{0,40}\b(?:license|licence|certification)\s+(?:is\s+)?required\b",

    r"\b(?:license|licence|certification)\s+(?:is\s+)?required\b",

    r"\brequired\s+certification\b",
]


# ============================================================
# RULE MATCHING
# ============================================================

def find_matches(
    text: str,
    patterns: list[str],
    category: str,
    reason: str,
) -> list[dict]:
    """
    Run a group of regex rules and return matching findings.
    """

    findings = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            findings.append(
                {
                    "category": (
                        category
                    ),

                    "reason": (
                        reason
                    ),

                    "evidence": (
                        extract_context(
                            text,
                            match.start(),
                            match.end(),
                        )
                    ),
                }
            )

    return findings


# ============================================================
# FINDING DEDUPLICATION
# ============================================================

def deduplicate_findings(
    findings: list[dict],
) -> list[dict]:
    """
    Keep only one finding per eligibility category.

    Multiple regex rules can match the same requirement.

    Example:

        SECURITY_CLEARANCE
        SECURITY_CLEARANCE

    becomes:

        SECURITY_CLEARANCE

    The first evidence snippet is retained.
    """

    unique = []

    seen_categories = set()

    for finding in findings:

        category = (
            finding[
                "category"
            ]
        )

        if (
            category
            in seen_categories
        ):

            continue

        seen_categories.add(
            category
        )

        unique.append(
            finding
        )

    return unique


# ============================================================
# MAIN ELIGIBILITY CHECK
# ============================================================

def evaluate_hard_eligibility(
    *,
    job_title: str,
    job_text: str,
) -> dict:
    """
    Evaluate applicant-specific eligibility requirements.

    Possible decisions:

        PASS

        NEEDS_ASSISTANCE

        SKIP


    V1 POLICY
    ---------

    Citizenship, clearance, export-control,
    sponsorship, license, and certification
    requirements are NOT guessed.

    If detected, they are routed to:

        NEEDS_ASSISTANCE


    SKIP is reserved for future rules where the
    applicant profile provides a deterministic
    known conflict.

    Example:

        applicant_has_active_clearance = False

        job requires active TS/SCI

    could eventually become:

        SKIP
    """

    # ========================================================
    # NORMALIZE
    # ========================================================

    title = (
        normalize_text(
            job_title
        )
    )

    text = (
        normalize_text(
            job_text
        )
    )

    combined = (
        f"{title}. {text}"
    )

    findings = []

    # ========================================================
    # SECURITY CLEARANCE
    # ========================================================

    if not has_exception(
        combined,
        CLEARANCE_EXCEPTIONS,
    ):

        findings.extend(
            find_matches(
                combined,
                CLEARANCE_PATTERNS,
                "SECURITY_CLEARANCE",
                (
                    "Job contains a security-clearance "
                    "requirement that must be reviewed."
                ),
            )
        )

    # ========================================================
    # CITIZENSHIP
    # ========================================================

    if not has_exception(
        combined,
        CITIZENSHIP_EXCEPTIONS,
    ):

        findings.extend(
            find_matches(
                combined,
                CITIZENSHIP_PATTERNS,
                "CITIZENSHIP",
                (
                    "Job contains a citizenship requirement "
                    "that must be reviewed."
                ),
            )
        )

    # ========================================================
    # EXPORT CONTROL
    # ========================================================

    findings.extend(
        find_matches(
            combined,
            EXPORT_CONTROL_PATTERNS,
            "EXPORT_CONTROL",
            (
                "Job contains an export-control or "
                "U.S.-person requirement that must "
                "be reviewed."
            ),
        )
    )

    # ========================================================
    # SPONSORSHIP
    # ========================================================

    findings.extend(
        find_matches(
            combined,
            SPONSORSHIP_PATTERNS,
            "SPONSORSHIP",
            (
                "Job contains a sponsorship restriction "
                "that must be reviewed."
            ),
        )
    )

    # ========================================================
    # LICENSE / CERTIFICATION
    # ========================================================

    findings.extend(
        find_matches(
            combined,
            LICENSE_CERT_PATTERNS,
            "LICENSE_OR_CERTIFICATION",
            (
                "Job appears to require a license "
                "or certification that must be verified."
            ),
        )
    )

    # ========================================================
    # REMOVE DUPLICATES
    # ========================================================

    findings = (
        deduplicate_findings(
            findings
        )
    )

    # ========================================================
    # PASS
    # ========================================================

    if not findings:

        return {
            "decision": (
                "PASS"
            ),

            "findings": [],

            "reason": None,
        }

    # ========================================================
    # NEEDS ASSISTANCE
    # ========================================================

    categories = sorted(
        {
            finding[
                "category"
            ]

            for finding
            in findings
        }
    )

    reason = (
        "Eligibility review required: "
        + ", ".join(
            categories
        )
    )

    return {
        "decision": (
            "NEEDS_ASSISTANCE"
        ),

        "findings": (
            findings
        ),

        "reason": (
            reason
        ),
    }
