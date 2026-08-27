import html
import re
from enum import Enum

from bs4 import BeautifulSoup


class ExperienceStatus(Enum):
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


PREFERRED_KEYWORDS = [
    "preferred",
    "nice to have",
    "nice-to-have",
    "bonus",
    "ideally",
    "a plus",
    "plus if",
    "preferred qualification",
    "preferred qualifications",
]


EXPERIENCE_TERMS = [
    "experience",
    "professional experience",
    "engineering experience",
    "software development experience",
    "software engineering experience",
    "software-engineering experience",
    "hands-on experience",
    "work experience",
    "industry experience",
    "development experience",
    "production experience",
]


def clean_job_content(content: str) -> str:
    """
    Convert Greenhouse HTML into normalized plain text.
    """

    if not content:
        return ""

    decoded = html.unescape(content)

    soup = BeautifulSoup(
        decoded,
        "html.parser",
    )

    text = soup.get_text(
        separator=" ",
        strip=True,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def get_context(
    text: str,
    start: int,
    end: int,
    radius: int = 140,
) -> str:
    """
    Return surrounding text for a detected years phrase.
    """

    left = max(
        0,
        start - radius,
    )

    right = min(
        len(text),
        end + radius,
    )

    return text[left:right].strip()


def looks_like_experience_context(
    context: str,
) -> bool:
    """
    Make sure the years refer to work/professional experience.
    """

    normalized = context.lower()

    return any(
        term in normalized
        for term in EXPERIENCE_TERMS
    )


def is_preferred_context(
    context: str,
) -> bool:
    """
    Determine whether the years requirement is described
    as preferred rather than expected/required.
    """

    normalized = context.lower()

    return any(
        keyword in normalized
        for keyword in PREFERRED_KEYWORDS
    )


def is_degree_duration(
    context: str,
    matched_text: str,
) -> bool:
    """
    Ignore phrases such as:

        4-year bachelor's degree
        3 or 4 year foreign degree

    while retaining real experience requirements.
    """

    normalized = context.lower()
    match_lower = matched_text.lower()

    degree_terms = [
        "year degree",
        "year bachelor's",
        "year bachelor",
        "year master's",
        "year master",
        "year university",
        "year college",
        "foreign degree",
    ]

    if any(
        term in normalized
        for term in degree_terms
    ):
        if "experience" not in match_lower:
            return True

    return False


def overlaps(
    start: int,
    end: int,
    occupied_spans: list[tuple[int, int]],
) -> bool:
    """
    Prevent part of a range from being detected again.

    Example:

        2-5 years

    should not later also become:

        5 years
    """

    return any(
        start < occupied_end
        and end > occupied_start
        for occupied_start, occupied_end
        in occupied_spans
    )


def find_experience_mentions(
    text: str,
) -> list[dict]:
    """
    Extract professional experience requirements.

    Handles examples such as:

        3 years
        4+ years
        2-5 years
        2-12+ years
        3 to 6 years
        at least 5 years
        minimum of 4 years

    More specific patterns run before simpler patterns.
    """

    if not text:
        return []

    patterns = [
        # -----------------------------------------------------
        # RANGE
        #
        # Examples:
        # 2-5 years
        # 2–12+ years
        # 3 to 6 years
        # -----------------------------------------------------
        (
            "range",
            re.compile(
                r"\b"
                r"(\d+)"
                r"\s*(?:-|–|—|to)\s*"
                r"(\d+)"
                r"\s*\+?"
                r"\s*(?:years?|yrs?)"
                r"\b",
                re.IGNORECASE,
            ),
        ),

        # -----------------------------------------------------
        # PLUS
        #
        # Example:
        # 5+ years
        # -----------------------------------------------------
        (
            "plus",
            re.compile(
                r"\b"
                r"(\d+)"
                r"\s*\+\s*"
                r"(?:years?|yrs?)"
                r"\b",
                re.IGNORECASE,
            ),
        ),

        # -----------------------------------------------------
        # AT LEAST
        #
        # Example:
        # at least 5 years
        # -----------------------------------------------------
        (
            "at_least",
            re.compile(
                r"\bat\s+least\s+"
                r"(\d+)"
                r"\s*(?:years?|yrs?)"
                r"\b",
                re.IGNORECASE,
            ),
        ),

        # -----------------------------------------------------
        # MINIMUM
        #
        # Example:
        # minimum of 4 years
        # -----------------------------------------------------
        (
            "minimum",
            re.compile(
                r"\bminimum(?:\s+of)?\s+"
                r"(\d+)"
                r"\s*(?:years?|yrs?)"
                r"\b",
                re.IGNORECASE,
            ),
        ),

        # -----------------------------------------------------
        # SINGLE
        #
        # Example:
        # 4 years
        # -----------------------------------------------------
        (
            "single",
            re.compile(
                r"\b"
                r"(\d+)"
                r"\s*(?:years?|yrs?)"
                r"\b",
                re.IGNORECASE,
            ),
        ),
    ]

    mentions = []
    occupied_spans = []

    for pattern_type, pattern in patterns:

        for match in pattern.finditer(text):

            start, end = match.span()

            # A more specific pattern already captured this area.
            if overlaps(
                start,
                end,
                occupied_spans,
            ):
                continue

            context = get_context(
                text,
                start,
                end,
            )

            if not looks_like_experience_context(
                context
            ):
                continue

            matched_text = match.group(0)

            if is_degree_duration(
                context,
                matched_text,
            ):

                nearby = text[
                    max(0, start - 25):
                    min(len(text), end + 50)
                ].lower()

                if "experience" not in nearby:
                    continue

            numbers = [
                int(value)
                for value in match.groups()
                if value is not None
            ]

            if not numbers:
                continue

            if pattern_type == "range":

                minimum_years = min(numbers)
                maximum_years = max(numbers)

            else:

                minimum_years = numbers[0]
                maximum_years = numbers[0]

            mentions.append(
                {
                    "text": context,
                    "match": matched_text,
                    "min_years": minimum_years,
                    "max_years": maximum_years,
                    "preferred": is_preferred_context(
                        context
                    ),
                    "type": pattern_type,
                }
            )

            occupied_spans.append(
                (start, end)
            )

    return mentions


def classify_experience(
    job: dict,
) -> tuple[ExperienceStatus, list[dict]]:
    """
    Apply our final V1 experience rules.

    ----------------------------------------------------------

    Preferred requirement:
        Ignore for blocking purposes.

    Minimum 0-3:
        ACCEPT

    Minimum 4:
        REVIEW

    Minimum 5+:
        REJECT

    ----------------------------------------------------------

    Ranges use the LOWER bound.

    Examples:

        0-2 years   -> ACCEPT
        2-5 years   -> ACCEPT
        2-12+ years -> ACCEPT
        3-6 years   -> ACCEPT
        4-6 years   -> REVIEW
        5-8 years   -> REJECT
        5+ years    -> REJECT
        8+ years    -> REJECT
    """

    content = job.get(
        "content",
        "",
    )

    text = clean_job_content(
        content
    )

    mentions = find_experience_mentions(
        text
    )

    if not mentions:
        return (
            ExperienceStatus.ACCEPT,
            [],
        )

    result = ExperienceStatus.ACCEPT

    for mention in mentions:

        # Preferred experience does not block application.
        if mention["preferred"]:
            continue

        minimum_years = mention[
            "min_years"
        ]

        # 5+ minimum is outside our target.
        if minimum_years >= 5:

            return (
                ExperienceStatus.REJECT,
                mentions,
            )

        # Exactly 4 goes to manual review.
        if minimum_years == 4:

            result = ExperienceStatus.REVIEW

    return (
        result,
        mentions,
    )


def filter_by_experience(
    jobs: list[dict],
):
    """
    Split jobs into:

        ACCEPT
        REVIEW
        REJECT
    """

    accepted_jobs = []
    review_jobs = []
    rejected_jobs = []

    for job in jobs:

        status, mentions = classify_experience(
            job
        )

        result = {
            "job": job,
            "experience_status": status,
            "experience_mentions": mentions,
        }

        if status == ExperienceStatus.ACCEPT:

            accepted_jobs.append(
                result
            )

        elif status == ExperienceStatus.REVIEW:

            review_jobs.append(
                result
            )

        else:

            rejected_jobs.append(
                result
            )

    return (
        accepted_jobs,
        review_jobs,
        rejected_jobs,
    )
