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


REQUIRED_KEYWORDS = [
    "required",
    "requirement",
    "requirements",
    "minimum",
    "minimum qualifications",
    "must have",
    "must-have",
    "must also have",
    "at least",
    "you have",
    "you bring",
    "looking for",
    "look for",
    "we look for",
    "we'd look for",
    "we would look for",
]


def clean_job_content(content: str) -> str:
    """
    Convert Greenhouse HTML job-description content into plain text.
    """

    if not content:
        return ""

    decoded = html.unescape(content)

    soup = BeautifulSoup(decoded, "html.parser")

    text = soup.get_text(separator="\n", strip=True)

    lines = []

    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()

        if cleaned:
            lines.append(cleaned)

    return "\n".join(lines)


def split_into_chunks(text: str) -> list[str]:
    """
    Break job-description text into manageable chunks.
    """

    if not text:
        return []

    chunks = []

    for line in text.splitlines():

        sentence_parts = re.split(
            r"(?<=[.!?])\s+",
            line,
        )

        for part in sentence_parts:
            part = part.strip()

            if part:
                chunks.append(part)

    return chunks


def is_preferred_context(text: str) -> bool:
    normalized = text.lower()

    return any(
        keyword in normalized
        for keyword in PREFERRED_KEYWORDS
    )


def is_required_context(text: str) -> bool:
    normalized = text.lower()

    return any(
        keyword in normalized
        for keyword in REQUIRED_KEYWORDS
    )


def looks_like_experience_context(text: str) -> bool:
    """
    Ignore year counts that refer to degrees, schooling,
    product age, etc.
    """

    normalized = text.lower()

    experience_terms = [
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

    return any(
        term in normalized
        for term in experience_terms
    )


def find_experience_mentions(text: str) -> list[dict]:
    """
    Find professional-experience requirements.

    More specific patterns are evaluated first so that a range
    such as "2-5 years" is not also detected as "5 years".
    """

    chunks = split_into_chunks(text)

    results = []

    patterns = [
        {
            "type": "range",
            "pattern": re.compile(
                r"\b(\d+)\s*(?:-|–|—|to)\s*(\d+)\s*"
                r"(?:\+?\s*)?(?:years?|yrs?)\b",
                re.IGNORECASE,
            ),
        },
        {
            "type": "plus",
            "pattern": re.compile(
                r"\b(\d+)\s*\+\s*(?:years?|yrs?)\b",
                re.IGNORECASE,
            ),
        },
        {
            "type": "at_least",
            "pattern": re.compile(
                r"\bat\s+least\s+(\d+)\s*(?:years?|yrs?)\b",
                re.IGNORECASE,
            ),
        },
        {
            "type": "minimum",
            "pattern": re.compile(
                r"\bminimum(?:\s+of)?\s+(\d+)\s*(?:years?|yrs?)\b",
                re.IGNORECASE,
            ),
        },
        {
            "type": "single",
            "pattern": re.compile(
                r"\b(\d+)\s*(?:years?|yrs?)\b",
                re.IGNORECASE,
            ),
        },
    ]

    for chunk in chunks:

        if not looks_like_experience_context(chunk):
            continue

        occupied_spans = []

        for pattern_info in patterns:

            pattern_type = pattern_info["type"]
            pattern = pattern_info["pattern"]

            for match in pattern.finditer(chunk):

                start, end = match.span()

                overlaps_existing = any(
                    start < existing_end
                    and end > existing_start
                    for existing_start, existing_end
                    in occupied_spans
                )

                if overlaps_existing:
                    continue

                groups = [
                    int(value)
                    for value in match.groups()
                    if value is not None
                ]

                if not groups:
                    continue

                if pattern_type == "range":
                    minimum_years = min(groups)
                    maximum_years = max(groups)

                else:
                    minimum_years = groups[0]
                    maximum_years = groups[0]

                preferred = is_preferred_context(chunk)
                required = is_required_context(chunk)

                results.append(
                    {
                        "text": chunk,
                        "match": match.group(0),
                        "min_years": minimum_years,
                        "max_years": maximum_years,
                        "preferred": preferred,
                        "required": required,
                        "type": pattern_type,
                    }
                )

                occupied_spans.append((start, end))

    return results


def classify_experience(
    job: dict,
) -> tuple[ExperienceStatus, list[dict]]:
    """
    Apply our experience eligibility rules.

    Rules
    -----
    Preferred requirement:
        Ignore it for blocking purposes.

    Minimum 0-3 years:
        ACCEPT

    Minimum 4 years:
        REVIEW

    Minimum 5+ years:
        REJECT

    For ranges, use the lower bound.

    Examples
    --------
    2-5 years -> ACCEPT
    3-6 years -> ACCEPT
    4-6 years -> REVIEW
    5-8 years -> REJECT
    6+ years  -> REJECT
    """

    content = job.get("content", "")

    text = clean_job_content(content)

    mentions = find_experience_mentions(text)

    if not mentions:
        return ExperienceStatus.ACCEPT, []

    strongest_status = ExperienceStatus.ACCEPT

    for mention in mentions:

        minimum_years = mention["min_years"]
        preferred = mention["preferred"]

        # A preferred qualification should not block us.
        if preferred:
            continue

        # 5+ minimum experience is outside our target.
        if minimum_years >= 5:
            return ExperienceStatus.REJECT, mentions

        # 4 years goes to manual review.
        if minimum_years == 4:
            strongest_status = ExperienceStatus.REVIEW

    return strongest_status, mentions


def filter_by_experience(jobs: list[dict]):
    """
    Split jobs into ACCEPT, REVIEW and REJECT buckets.
    """

    accepted_jobs = []
    review_jobs = []
    rejected_jobs = []

    for job in jobs:

        status, mentions = classify_experience(job)

        result = {
            "job": job,
            "experience_status": status,
            "experience_mentions": mentions,
        }

        if status == ExperienceStatus.ACCEPT:
            accepted_jobs.append(result)

        elif status == ExperienceStatus.REVIEW:
            review_jobs.append(result)

        else:
            rejected_jobs.append(result)

    return (
        accepted_jobs,
        review_jobs,
        rejected_jobs,
    )
