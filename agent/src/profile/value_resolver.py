from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)
from pathlib import Path
from typing import Any

from src.profile.applicant_profile import (
    ApplicantProfile,
)


STATUS_READY = "READY"
STATUS_REQUIRED_ASSISTANCE = "REQUIRED_ASSISTANCE"
STATUS_OPTIONAL_ASSISTANCE = "OPTIONAL_ASSISTANCE"
STATUS_MISSING_REQUIRED_PROFILE = "MISSING_REQUIRED_PROFILE"
STATUS_OPTIONAL_MISSING = "OPTIONAL_MISSING"
STATUS_MISSING_RESUME = "MISSING_RESUME"
STATUS_POLICY_MISMATCH = "POLICY_MISMATCH"
STATUS_IGNORED = "IGNORED"


PROFILE_VALUE_PATHS = {
    "FIRST_NAME": (
        "identity",
        "first_name",
    ),
    "LAST_NAME": (
        "identity",
        "last_name",
    ),
    "PREFERRED_FIRST_NAME": (
        "identity",
        "preferred_first_name",
    ),
    "EMAIL": (
        "contact",
        "email",
    ),
    "PHONE": (
        "contact",
        "phone",
    ),
    "LINKEDIN_URL": (
        "links",
        "linkedin_url",
    ),
    "PORTFOLIO_URL": (
        "links",
        "portfolio_url",
    ),
    "GITHUB_URL": (
        "links",
        "github_url",
    ),
    "COUNTRY": (
        "address",
        "country",
    ),
    "CITY": (
        "address",
        "city",
    ),
    "STATE_OR_PROVINCE": (
        "address",
        "state_or_province",
    ),
    "POSTAL_CODE": (
        "address",
        "postal_code",
    ),
    "STREET_ADDRESS": (
        "address",
        "street_address",
    ),
    "LOCATION_FREEFORM": (
        "address",
        "location_freeform",
    ),
    "CURRENT_US_LOCATION": (
        "address",
        "currently_in_us",
    ),
    "EDUCATION_SCHOOL": (
        "education",
        "school",
    ),
    "EDUCATION_DEGREE": (
        "education",
        "degree",
    ),
    "EDUCATION_DISCIPLINE": (
        "education",
        "discipline",
    ),
}


SENSITIVE_KEYS = {
    "EMAIL",
    "PHONE",
    "STREET_ADDRESS",
    "POSTAL_CODE",
}


@dataclass
class ResolvedField:
    label: str
    category: str
    original_action: str
    answer_key: str | None
    required: bool
    status: str
    source: str
    reason: str
    value: Any = None
    classifier_policy_hint: Any = None

    def public_dict(
        self,
        *,
        include_values: bool = False,
    ) -> dict:
        result = asdict(
            self
        )

        if include_values:
            return result

        value_present = (
            self.value is not None
            and self.value != ""
        )

        result.pop(
            "value",
            None,
        )

        result[
            "value_present"
        ] = value_present

        if (
            value_present
            and self.answer_key
            in SENSITIVE_KEYS
        ):
            result[
                "value_preview"
            ] = "<redacted>"

        elif value_present:
            result[
                "value_preview"
            ] = str(
                self.value
            )

        return result


def _yes_no(
    value: bool,
) -> str:
    return (
        "Yes"
        if value
        else "No"
    )


def _resolve_policy_answer(
    *,
    answer_key: str,
    profile: ApplicantProfile,
) -> tuple[
    str | None,
    str,
]:
    authorized = profile.get(
        "work_authorization",
        "authorized_to_work_us",
    )

    sponsorship_now = profile.get(
        "work_authorization",
        "sponsorship_now",
    )

    sponsorship_future = profile.get(
        "work_authorization",
        "sponsorship_future",
    )

    if answer_key == "WORK_AUTHORIZED_US":
        if not isinstance(
            authorized,
            bool,
        ):
            return (
                None,
                "authorized_to_work_us is missing from the applicant profile.",
            )

        return (
            _yes_no(
                authorized
            ),
            "Resolved from explicit work-authorization profile fact.",
        )

    if answer_key == "SPONSORSHIP_NOW":
        if not isinstance(
            sponsorship_now,
            bool,
        ):
            return (
                None,
                "sponsorship_now is missing from the applicant profile.",
            )

        return (
            _yes_no(
                sponsorship_now
            ),
            "Resolved from explicit current sponsorship profile fact.",
        )

    if answer_key == "SPONSORSHIP_FUTURE":
        if not isinstance(
            sponsorship_future,
            bool,
        ):
            return (
                None,
                "sponsorship_future is missing from the applicant profile.",
            )

        return (
            _yes_no(
                sponsorship_future
            ),
            "Resolved from explicit future sponsorship profile fact.",
        )

    if answer_key == "SPONSORSHIP_NOW_OR_FUTURE":
        if (
            not isinstance(
                sponsorship_now,
                bool,
            )
            or not isinstance(
                sponsorship_future,
                bool,
            )
        ):
            return (
                None,
                "Current/future sponsorship facts are incomplete.",
            )

        return (
            _yes_no(
                sponsorship_now
                or sponsorship_future
            ),
            "Resolved as logical OR of current and future sponsorship.",
        )

    if answer_key == "WORK_AUTH_WITHOUT_SPONSORSHIP_NOW":
        if (
            not isinstance(
                authorized,
                bool,
            )
            or not isinstance(
                sponsorship_now,
                bool,
            )
        ):
            return (
                None,
                "Current work-authorization/sponsorship facts are incomplete.",
            )

        return (
            _yes_no(
                authorized
                and not sponsorship_now
            ),
            (
                "Resolved from current work authorization and "
                "current sponsorship requirement."
            ),
        )

    if answer_key == "WORK_AUTH_WITHOUT_SPONSORSHIP_FUTURE":
        if (
            not isinstance(
                authorized,
                bool,
            )
            or not isinstance(
                sponsorship_now,
                bool,
            )
            or not isinstance(
                sponsorship_future,
                bool,
            )
        ):
            return (
                None,
                "Work-authorization/sponsorship facts are incomplete.",
            )

        return (
            _yes_no(
                authorized
                and not sponsorship_now
                and not sponsorship_future
            ),
            (
                "Resolved from current authorization plus both "
                "current and future sponsorship requirements."
            ),
        )

    return (
        None,
        (
            "No safe policy resolver is registered for "
            f"answer key {answer_key!r}."
        ),
    )


def _resolve_profile_value(
    *,
    answer_key: str,
    profile: ApplicantProfile,
) -> tuple[
    Any,
    str,
]:
    if answer_key == "FULL_NAME":
        value = profile.full_name()

        return (
            value,
            "Derived from explicit first and last name profile facts.",
        )

    path = PROFILE_VALUE_PATHS.get(
        answer_key
    )

    if path is None:
        return (
            None,
            (
                "No safe applicant-profile mapping is registered "
                f"for answer key {answer_key!r}."
            ),
        )

    value = profile.get(
        *path
    )

    if (
        answer_key
        == "CURRENT_US_LOCATION"
        and isinstance(
            value,
            bool,
        )
    ):
        value = _yes_no(
            value
        )

    return (
        value,
        (
            "Resolved from applicant profile path: "
            + ".".join(
                path
            )
        ),
    )


def resolve_field(
    *,
    field: dict,
    profile: ApplicantProfile,
    resume_path: str | Path | None = None,
) -> ResolvedField:
    decision = (
        field.get(
            "decision"
        )
        or {}
    )

    action = (
        decision.get(
            "action"
        )
        or "UNKNOWN"
    )

    category = (
        decision.get(
            "category"
        )
        or "UNKNOWN"
    )

    answer_key = (
        decision.get(
            "answer_key"
        )
    )

    required = bool(
        field.get(
            "required"
        )
    )

    label = (
        field.get(
            "label"
        )
        or "[unlabeled field]"
    )

    classifier_hint = (
        decision.get(
            "fixed_answer"
        )
    )

    if action == "IGNORE":
        return ResolvedField(
            label=label,
            category=category,
            original_action=action,
            answer_key=answer_key,
            required=required,
            status=STATUS_IGNORED,
            source="none",
            reason="Technical/non-applicant control.",
        )

    if action == "NEEDS_ASSISTANCE":
        return ResolvedField(
            label=label,
            category=category,
            original_action=action,
            answer_key=answer_key,
            required=required,
            status=(
                STATUS_REQUIRED_ASSISTANCE
                if required
                else STATUS_OPTIONAL_ASSISTANCE
            ),
            source="human",
            reason=(
                decision.get(
                    "reason"
                )
                or "Human review required."
            ),
        )

    if action == "RESUME_FILE":
        if resume_path is None:
            return ResolvedField(
                label=label,
                category=category,
                original_action=action,
                answer_key=answer_key,
                required=True,
                status=STATUS_MISSING_RESUME,
                source="matcher",
                reason=(
                    "No selected resume path was supplied to the resolver."
                ),
            )

        resume = Path(
            resume_path
        )

        if not resume.is_file():
            return ResolvedField(
                label=label,
                category=category,
                original_action=action,
                answer_key=answer_key,
                required=True,
                status=STATUS_MISSING_RESUME,
                source="matcher",
                reason=(
                    f"Selected resume does not exist: {resume}"
                ),
            )

        return ResolvedField(
            label=label,
            category=category,
            original_action=action,
            answer_key=answer_key,
            required=True,
            status=STATUS_READY,
            source="matcher",
            reason="Selected resume file exists and is ready for later upload.",
            value=str(
                resume.resolve()
            ),
        )

    if action == "PROFILE_VALUE":
        if not answer_key:
            return ResolvedField(
                label=label,
                category=category,
                original_action=action,
                answer_key=None,
                required=required,
                status=(
                    STATUS_MISSING_REQUIRED_PROFILE
                    if required
                    else STATUS_OPTIONAL_MISSING
                ),
                source="profile",
                reason="Profile field has no answer key.",
            )

        value, reason = _resolve_profile_value(
            answer_key=answer_key,
            profile=profile,
        )

        missing = (
            value is None
            or value == ""
        )

        if missing:
            return ResolvedField(
                label=label,
                category=category,
                original_action=action,
                answer_key=answer_key,
                required=required,
                status=(
                    STATUS_MISSING_REQUIRED_PROFILE
                    if required
                    else STATUS_OPTIONAL_MISSING
                ),
                source="profile",
                reason=reason,
            )

        return ResolvedField(
            label=label,
            category=category,
            original_action=action,
            answer_key=answer_key,
            required=required,
            status=STATUS_READY,
            source="profile",
            reason=reason,
            value=value,
        )

    if action == "FIXED_ANSWER":
        if not answer_key:
            return ResolvedField(
                label=label,
                category=category,
                original_action=action,
                answer_key=None,
                required=required,
                status=(
                    STATUS_REQUIRED_ASSISTANCE
                    if required
                    else STATUS_OPTIONAL_ASSISTANCE
                ),
                source="policy",
                reason="Fixed-answer field has no answer key.",
            )

        value, reason = _resolve_policy_answer(
            answer_key=answer_key,
            profile=profile,
        )

        if value is None:
            return ResolvedField(
                label=label,
                category=category,
                original_action=action,
                answer_key=answer_key,
                required=required,
                status=(
                    STATUS_REQUIRED_ASSISTANCE
                    if required
                    else STATUS_OPTIONAL_ASSISTANCE
                ),
                source="profile-policy",
                reason=reason,
                classifier_policy_hint=classifier_hint,
            )

        if (
            classifier_hint is not None
            and str(
                classifier_hint
            ).strip().lower()
            != str(
                value
            ).strip().lower()
        ):
            return ResolvedField(
                label=label,
                category=category,
                original_action=action,
                answer_key=answer_key,
                required=required,
                status=STATUS_POLICY_MISMATCH,
                source="profile-policy",
                reason=(
                    "Classifier policy hint disagrees with the "
                    "current applicant profile. Human review is "
                    "required before any browser filling."
                ),
                value=value,
                classifier_policy_hint=classifier_hint,
            )

        return ResolvedField(
            label=label,
            category=category,
            original_action=action,
            answer_key=answer_key,
            required=required,
            status=STATUS_READY,
            source="profile-policy",
            reason=reason,
            value=value,
            classifier_policy_hint=classifier_hint,
        )

    return ResolvedField(
        label=label,
        category=category,
        original_action=action,
        answer_key=answer_key,
        required=required,
        status=(
            STATUS_REQUIRED_ASSISTANCE
            if required
            else STATUS_OPTIONAL_ASSISTANCE
        ),
        source="unknown",
        reason=(
            f"Unsupported field action {action!r}; "
            "resolver will not guess."
        ),
    )


def resolve_application(
    *,
    inspection: dict,
    profile: ApplicantProfile,
    resume_path: str | Path | None = None,
) -> dict:
    resolved_fields = [
        resolve_field(
            field=field,
            profile=profile,
            resume_path=resume_path,
        )
        for field in (
            inspection.get(
                "fields"
            )
            or []
        )
    ]

    blocking_statuses = {
        STATUS_REQUIRED_ASSISTANCE,
        STATUS_MISSING_REQUIRED_PROFILE,
        STATUS_MISSING_RESUME,
        STATUS_POLICY_MISMATCH,
    }

    required_unresolved = [
        field
        for field in resolved_fields
        if field.status
        in blocking_statuses
    ]

    counts = {}

    for field in resolved_fields:
        counts[
            field.status
        ] = (
            counts.get(
                field.status,
                0,
            )
            + 1
        )

    return {
        "requested_url": inspection.get(
            "requested_url"
        ),
        "page_title": inspection.get(
            "page_title"
        ),
        "fields": resolved_fields,
        "summary": {
            "total_fields": len(
                resolved_fields
            ),
            "ready_fields": counts.get(
                STATUS_READY,
                0,
            ),
            "required_unresolved": len(
                required_unresolved
            ),
            "optional_unresolved": (
                counts.get(
                    STATUS_OPTIONAL_ASSISTANCE,
                    0,
                )
                + counts.get(
                    STATUS_OPTIONAL_MISSING,
                    0,
                )
            ),
            "policy_mismatches": counts.get(
                STATUS_POLICY_MISMATCH,
                0,
            ),
            "missing_resume": counts.get(
                STATUS_MISSING_RESUME,
                0,
            ),
            "ready_for_submission": (
                len(
                    required_unresolved
                )
                == 0
            ),
            "browser_modified": False,
            "submit_attempted": False,
        },
    }
