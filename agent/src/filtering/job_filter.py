import re


TARGET_ROLE_PATTERNS = [
    r"\bsoftware engineer\b",
    r"\bsoftware development engineer\b",
    r"\bsoftware developer\b",
    r"\bbackend engineer\b",
    r"\bback-end engineer\b",
    r"\bfrontend engineer\b",
    r"\bfront-end engineer\b",
    r"\bfull stack engineer\b",
    r"\bfull-stack engineer\b",
    r"\bmachine learning engineer\b",
    r"\bml engineer\b",
    r"\bai engineer\b",
    r"\bartificial intelligence engineer\b",
    r"\bgenerative ai engineer\b",
    r"\bgenai engineer\b",
    r"\bsystems engineer\b",
    r"\bsystem engineer\b",
    r"\bproduction support engineer\b",
    r"\bapplication support engineer\b",
    r"\bdevops engineer\b",
    r"\bsite reliability engineer\b",
    r"\bsre\b",
]


SENIORITY_EXCLUSIONS = [
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\blead\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\barchitect\b",
    r"\bvice president\b",
    r"\bvp\b",
    r"\bhead\b",
]


def is_target_role(title: str) -> bool:
    """
    Return True when the job title matches one of our target roles.
    """
    title = title.lower().strip()

    return any(
        re.search(pattern, title, re.IGNORECASE)
        for pattern in TARGET_ROLE_PATTERNS
    )


def has_excluded_seniority(title: str) -> bool:
    """
    Return True when the title clearly indicates an excluded seniority level.
    """
    title = title.lower().strip()

    return any(
        re.search(pattern, title, re.IGNORECASE)
        for pattern in SENIORITY_EXCLUSIONS
    )


def filter_by_role(jobs: list[dict]) -> list[dict]:
    """
    Keep target engineering roles and remove clearly senior positions.
    """
    filtered_jobs = []

    for job in jobs:
        title = job.get("title", "")

        if not is_target_role(title):
            continue

        if has_excluded_seniority(title):
            continue

        filtered_jobs.append(job)

    return filtered_jobs
