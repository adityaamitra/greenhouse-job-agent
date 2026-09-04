from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any

from src.profile.applicant_profile import ApplicantProfile
from src.profile.value_resolver import (
    STATUS_READY,
    resolve_application,
)


ROUTE_AGENT_CONTINUE = "AGENT_CONTINUE"
ROUTE_NEEDS_ASSISTANCE = "NEEDS_ASSISTANCE"


SENSITIVE_ANSWER_KEYS = {
    "FIRST_NAME",
    "LAST_NAME",
    "PREFERRED_FIRST_NAME",
    "EMAIL",
    "PHONE",
    "COUNTRY",
    "CITY",
    "STATE_OR_PROVINCE",
    "POSTAL_CODE",
    "STREET_ADDRESS",
    "LOCATION_FREEFORM",
    "CURRENT_US_LOCATION",
    "LINKEDIN_URL",
    "PORTFOLIO_URL",
    "GITHUB_URL",
    "EDUCATION_SCHOOL",
    "EDUCATION_DEGREE",
    "EDUCATION_DISCIPLINE",
    "FULL_NAME",
}


POLICY_ANSWER_KEYS = {
    "WORK_AUTHORIZED_US",
    "SPONSORSHIP_NOW",
    "SPONSORSHIP_FUTURE",
    "SPONSORSHIP_NOW_OR_FUTURE",
    "WORK_AUTH_WITHOUT_SPONSORSHIP_NOW",
    "WORK_AUTH_WITHOUT_SPONSORSHIP_FUTURE",
}


@dataclass
class HandoffItem:
    label: str
    category: str
    required: bool
    status: str
    source: str
    answer_key: str | None = None
    display_answer: str | None = None
    reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_page_title(
    page_title: str | None,
) -> tuple[str | None, str | None]:
    """
    Parse common Greenhouse title:
      Job Application for <ROLE> at <COMPANY>
    """
    if not page_title:
        return (None, None)

    match = re.match(
        r"^\s*Job Application for\s+(.+?)\s+at\s+(.+?)\s*$",
        page_title,
        flags=re.IGNORECASE,
    )

    if not match:
        return (None, None)

    return (
        match.group(1).strip(),
        match.group(2).strip(),
    )


def _policy_display_answer(
    *,
    answer_key: str | None,
    value: Any,
) -> str | None:
    if (
        answer_key in POLICY_ANSWER_KEYS
        and value not in (
            None,
            "",
        )
    ):
        return str(value)

    return None


def _field_to_handoff_item(
    resolved_field,
) -> HandoffItem:
    return HandoffItem(
        label=resolved_field.label,
        category=resolved_field.category,
        required=resolved_field.required,
        status=resolved_field.status,
        source=resolved_field.source,
        answer_key=resolved_field.answer_key,
        display_answer=_policy_display_answer(
            answer_key=resolved_field.answer_key,
            value=resolved_field.value,
        ),
        reason=resolved_field.reason,
    )


def _challenge_from_fill_report(
    fill_report: dict | None,
) -> tuple[bool, list[str]]:
    if not fill_report:
        return (
            False,
            [],
        )

    summary = (
        fill_report.get(
            "fill_summary"
        )
        or {}
    )

    detected = bool(
        summary.get(
            "page_challenge_detected"
        )
    )

    reasons = [
        str(
            reason
        )
        for reason in (
            summary.get(
                "page_challenge_reasons"
            )
            or []
        )
        if str(
            reason
        ).strip()
    ]

    return (
        detected,
        reasons,
    )


def build_assistance_handoff(
    *,
    inspection: dict,
    profile: ApplicantProfile,
    resume_path: str | Path | None,
    fill_report: dict | None = None,
    company: str | None = None,
    job_title: str | None = None,
) -> dict:
    """
    Build a compact, redacted application handoff packet.

    This function does not open a browser, fill a field, upload a file,
    or submit an application.
    """

    resolution = resolve_application(
        inspection=inspection,
        profile=profile,
        resume_path=resume_path,
    )

    parsed_job_title, parsed_company = _parse_page_title(
        inspection.get(
            "page_title"
        )
    )

    final_company = (
        company
        or parsed_company
    )

    final_job_title = (
        job_title
        or parsed_job_title
    )

    ready_items = []
    assistance_items = []
    blocking_items = []

    for resolved_field in resolution[
        "fields"
    ]:
        item = _field_to_handoff_item(
            resolved_field
        )

        if resolved_field.status == STATUS_READY:
            ready_items.append(
                item
            )
        else:
            assistance_items.append(
                item
            )

            if resolved_field.required:
                blocking_items.append(
                    item
                )

    challenge_detected, challenge_reasons = _challenge_from_fill_report(
        fill_report
    )

    fill_failures = []

    if fill_report:
        fill_failures = [
            result
            for result in (
                fill_report.get(
                    "fill_results"
                )
                or []
            )
            if (
                isinstance(
                    result,
                    dict,
                )
                and result.get(
                    "status"
                )
                == "FILL_FAILED"
            )
        ]

    failed_answer_keys = {
        result.get(
            "answer_key"
        )
        for result in (
            fill_failures
        )
        if result.get(
            "answer_key"
        )
    }

    if failed_answer_keys:
        ready_items = [
            item
            for item in (
                ready_items
            )
            if item.answer_key
            not in failed_answer_keys
        ]

    for failure in fill_failures:
        failure_item = HandoffItem(
            label=str(
                failure.get(
                    "label"
                )
                or "[unlabeled field]"
            ),
            category=str(
                failure.get(
                    "category"
                )
                or "BROWSER_FILL_FAILURE"
            ),
            required=bool(
                failure.get(
                    "required"
                )
            ),
            status="FILL_FAILED",
            source=str(
                failure.get(
                    "source"
                )
                or "browser"
            ),
            answer_key=(
                failure.get(
                    "answer_key"
                )
            ),
            display_answer=None,
            reason=str(
                failure.get(
                    "reason"
                )
                or "Deterministic browser fill failed."
            ),
        )

        assistance_items.append(
            failure_item
        )

        if failure_item.required:
            blocking_items.append(
                failure_item
            )

    nonready_mutation_detected = False
    nonready_mutation_reason = ""

    if fill_report:
        fill_summary = (
            fill_report.get(
                "fill_summary"
            )
            or {}
        )

        nonready_mutation_detected = bool(
            fill_summary.get(
                "nonready_mutation_detected"
            )
        )

        nonready_mutation_reason = str(
            fill_summary.get(
                "nonready_mutation_reason"
            )
            or ""
        )

    route_reasons = []

    if challenge_detected:
        route_reasons.append(
            "Page challenge / CAPTCHA detected."
        )

    if fill_failures:
        route_reasons.append(
            f"{len(fill_failures)} deterministic browser fill(s) failed."
        )

    submit_attempts_blocked = 0

    if fill_report:
        submit_attempts_blocked = int(
            (
                fill_report.get(
                    "fill_summary"
                )
                or {}
            ).get(
                "submit_attempts_blocked"
            )
            or 0
        )

    if submit_attempts_blocked:
        route_reasons.append(
            "A form submission attempt was blocked by the browser safety guard."
        )

    if blocking_items:
        route_reasons.append(
            f"{len(blocking_items)} required field(s) need human resolution."
        )

    if resolution[
        "summary"
    ][
        "policy_mismatches"
    ]:
        route_reasons.append(
            "Policy mismatch detected."
        )

    if resolution[
        "summary"
    ][
        "missing_resume"
    ]:
        route_reasons.append(
            "Selected resume is missing."
        )

    if nonready_mutation_detected:
        route_reasons.append(
            "Browser contamination safety violation detected."
        )

    route = (
        ROUTE_NEEDS_ASSISTANCE
        if route_reasons
        else ROUTE_AGENT_CONTINUE
    )

    resume_name = None

    if resume_path:
        resume_name = Path(
            resume_path
        ).name

    return {
        "packet_version": 1,
        "company": final_company,
        "job_title": final_job_title,
        "requested_url": inspection.get(
            "requested_url"
        ),
        "page_title": inspection.get(
            "page_title"
        ),
        "selected_resume": resume_name,
        "route": route,
        "route_reasons": route_reasons,
        "challenge": {
            "detected": challenge_detected,
            "reasons": challenge_reasons,
        },
        "browser_safety": {
            "application_submitted": False,
            "submit_clicked_by_agent": False,
            "nonready_mutation_detected": nonready_mutation_detected,
            "nonready_mutation_reason": nonready_mutation_reason,
        },
        "deterministic_ready": [
            item.to_dict()
            for item in ready_items
        ],
        "human_assistance": [
            item.to_dict()
            for item in assistance_items
        ],
        "summary": {
            "ready_count": len(
                ready_items
            ),
            "human_assistance_count": len(
                assistance_items
            ),
            "required_human_count": len(
                blocking_items
            ),
            "challenge_detected": challenge_detected,
            "policy_mismatches": resolution[
                "summary"
            ][
                "policy_mismatches"
            ],
            "missing_resume": resolution[
                "summary"
            ][
                "missing_resume"
            ],
        },
    }


def render_handoff_markdown(
    packet: dict,
) -> str:
    lines = []

    company = (
        packet.get(
            "company"
        )
        or "Unknown company"
    )

    job_title = (
        packet.get(
            "job_title"
        )
        or "Unknown job"
    )

    lines.append(
        "# Browser Assistance Handoff"
    )
    lines.append("")
    lines.append(
        f"**Company:** {company}"
    )
    lines.append(
        f"**Job:** {job_title}"
    )

    if packet.get(
        "selected_resume"
    ):
        lines.append(
            f"**Selected resume:** `{packet['selected_resume']}`"
        )

    lines.append(
        f"**Recommended route:** `{packet['route']}`"
    )

    route_reasons = (
        packet.get(
            "route_reasons"
        )
        or []
    )

    if route_reasons:
        lines.append("")
        lines.append(
            "## Why this route"
        )

        for reason in route_reasons:
            lines.append(
                f"- {reason}"
            )

    lines.append("")
    lines.append(
        "## Deterministic answers ready"
    )

    ready = (
        packet.get(
            "deterministic_ready"
        )
        or []
    )

    if not ready:
        lines.append(
            "- None"
        )

    for item in ready:
        label = item.get(
            "label"
        ) or "[unlabeled]"

        display_answer = item.get(
            "display_answer"
        )

        if display_answer is not None:
            lines.append(
                f"- ✓ {label} → **{display_answer}**"
            )
        else:
            lines.append(
                f"- ✓ {label} → ready"
            )

    lines.append("")
    lines.append(
        "## Human input / review needed"
    )

    assistance = (
        packet.get(
            "human_assistance"
        )
        or []
    )

    if not assistance:
        lines.append(
            "- None"
        )

    for item in assistance:
        marker = (
            "!"
            if item.get(
                "required"
            )
            else "○"
        )

        label = item.get(
            "label"
        ) or "[unlabeled]"

        category = item.get(
            "category"
        ) or "UNKNOWN"

        requirement = (
            "required"
            if item.get(
                "required"
            )
            else "optional"
        )

        lines.append(
            f"- {marker} {label} "
            f"(`{category}`, {requirement})"
        )

    challenge = (
        packet.get(
            "challenge"
        )
        or {}
    )

    if challenge.get(
        "detected"
    ):
        lines.append("")
        lines.append(
            "## Browser challenge"
        )
        lines.append(
            "- ! CAPTCHA / anti-bot challenge detected."
        )

        for reason in (
            challenge.get(
                "reasons"
            )
            or []
        ):
            lines.append(
                f"- {reason}"
            )

    lines.append("")
    lines.append(
        "## Safety status"
    )
    lines.append(
        "- Application submitted: **NO**"
    )
    lines.append(
        "- Submit clicked by agent: **NO**"
    )

    if (
        packet.get(
            "browser_safety",
            {}
        ).get(
            "nonready_mutation_detected"
        )
    ):
        lines.append(
            "- Non-ready mutation detected: **YES**"
        )
    else:
        lines.append(
            "- Non-ready mutation detected: **NO**"
        )

    lines.append("")

    return "\n".join(
        lines
    )
