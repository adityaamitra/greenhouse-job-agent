import re


# ============================================================
# PROFILE NAMES
#
# These names should match the master resume names already
# used by the matcher.
# ============================================================

SOFTWARE_ENGINEER = "software_engineer"

BACKEND_ENGINEER = "backend_engineer"

FRONTEND_ENGINEER = "frontend_engineer"

FULLSTACK_ENGINEER = "fullstack_engineer"

AI_ML_ENGINEER = "ai_ml_engineer"

SYSTEMS_ENGINEER = "systems_engineer"

PRODUCTION_SUPPORT_ENGINEER = (
    "production_support_engineer"
)

DEVOPS_ENGINEER = "devops_engineer"


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_title(
    title: str,
) -> str:
    """
    Normalize a job title for rule matching.
    """

    if not title:
        return ""

    normalized = (
        title
        .lower()
        .strip()
    )

    normalized = re.sub(
        r"[_/]",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized


def contains_pattern(
    text: str,
    patterns: list[str],
) -> bool:

    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


# ============================================================
# PROFILE PATTERNS
# ============================================================

AI_ML_PATTERNS = [
    r"\bmachine learning\b",
    r"\bml engineer\b",
    r"\bai engineer\b",
    r"\bartificial intelligence\b",

    # GenAI spelling variations
    r"\bgen\s*ai\b",
    r"\bgenai\b",
    r"\bgenerative\s+ai\b",
    r"\bgenerative\s+artificial intelligence\b",

    # AI-specialized software engineering
    r"\bai enablement\b",
    r"\benterprise ai\b",
    r"\bai infrastructure\b",
    r"\bai platform\b",
    r"\bai systems\b",
    r"\bai tooling\b",

    # Common ML specialties
    r"\bml infrastructure\b",
    r"\bml platform\b",
    r"\bml systems\b",
    r"\bmlops\b",
    r"\bdeep learning\b",
    r"\bnlp\b",
    r"\bnatural language processing\b",
    r"\bcomputer vision\b",
    r"\bllm\b",
    r"\blarge language model",
]


FRONTEND_PATTERNS = [
    r"\bfront[\s-]?end\b",
    r"\bfrontend\b",
    r"\bui engineer\b",
    r"\bweb ui\b",
]


FULLSTACK_PATTERNS = [
    r"\bfull[\s-]?stack\b",
    r"\bfullstack\b",
]


BACKEND_PATTERNS = [
    r"\bback[\s-]?end\b",
    r"\bbackend\b",
    r"\bserver[\s-]?side\b",
]


DEVOPS_PATTERNS = [
    r"\bdevops\b",
    r"\bsite reliability\b",
    r"\bsre\b",
    r"\bplatform operations\b",
    r"\bcloud operations\b",
]


PRODUCTION_SUPPORT_PATTERNS = [
    r"\bproduction support\b",
    r"\bapplication support\b",
    r"\btechnical support engineer\b",
    r"\bsupport engineer\b",
    r"\bproduction engineer\b",
]


SYSTEMS_PATTERNS = [
    r"\bsystems engineer\b",
    r"\bsystem engineer\b",
    r"\bit systems\b",
    r"\binfrastructure systems engineer\b",
]


# ============================================================
# CLASSIFIER
# ============================================================

def classify_job_profile(
    job_title: str,
) -> str:
    """
    Classify a job title into one of the 8 resume profiles.

    Precedence is important.

    Example:

        Software Engineer, Gen AI

    contains "Software Engineer" but should be considered
    AI/ML specialized.

    Likewise:

        Software Engineer - Full Stack

    should route to Fullstack rather than generic Software.
    """

    title = normalize_title(
        job_title
    )

    # --------------------------------------------------------
    # AI / ML
    #
    # Check this before generic Software Engineer.
    # --------------------------------------------------------

    if contains_pattern(
        title,
        AI_ML_PATTERNS,
    ):

        return AI_ML_ENGINEER

    # --------------------------------------------------------
    # FULL STACK
    # --------------------------------------------------------

    if contains_pattern(
        title,
        FULLSTACK_PATTERNS,
    ):

        return FULLSTACK_ENGINEER

    # --------------------------------------------------------
    # FRONTEND
    # --------------------------------------------------------

    if contains_pattern(
        title,
        FRONTEND_PATTERNS,
    ):

        return FRONTEND_ENGINEER

    # --------------------------------------------------------
    # BACKEND
    # --------------------------------------------------------

    if contains_pattern(
        title,
        BACKEND_PATTERNS,
    ):

        return BACKEND_ENGINEER

    # --------------------------------------------------------
    # DEVOPS / SRE
    # --------------------------------------------------------

    if contains_pattern(
        title,
        DEVOPS_PATTERNS,
    ):

        return DEVOPS_ENGINEER

    # --------------------------------------------------------
    # PRODUCTION SUPPORT
    # --------------------------------------------------------

    if contains_pattern(
        title,
        PRODUCTION_SUPPORT_PATTERNS,
    ):

        return PRODUCTION_SUPPORT_ENGINEER

    # --------------------------------------------------------
    # SYSTEMS
    # --------------------------------------------------------

    if contains_pattern(
        title,
        SYSTEMS_PATTERNS,
    ):

        return SYSTEMS_ENGINEER

    # --------------------------------------------------------
    # DEFAULT
    #
    # Generic Software Engineer and ambiguous engineering
    # titles use the software engineering profile.
    # --------------------------------------------------------

    return SOFTWARE_ENGINEER
