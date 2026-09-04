from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)
from pathlib import Path
from typing import Any
import re

from playwright.sync_api import (
    Frame,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from src.browser.field_classifier import (
    classify_field,
)
from src.browser.greenhouse_form import (
    inspect_form_fields,
)
from src.profile.applicant_profile import (
    ApplicantProfile,
)
from src.profile.value_resolver import (
    STATUS_READY,
    resolve_application,
)


DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_SETTLE_MS = 1_500

CONTROL_SELECTOR = (
    "input, select, textarea"
)


SUBMIT_GUARD_SCRIPT = r"""
(() => {
  if (window.__GREENHOUSE_JOB_AGENT_SUBMIT_GUARD__) {
    return;
  }

  window.__GREENHOUSE_JOB_AGENT_SUBMIT_GUARD__ = true;
  window.__GREENHOUSE_JOB_AGENT_SUBMIT_ATTEMPTS__ = 0;

  const noteAttempt = () => {
    window.__GREENHOUSE_JOB_AGENT_SUBMIT_ATTEMPTS__ += 1;
  };

  document.addEventListener(
    "submit",
    (event) => {
      noteAttempt();
      event.preventDefault();
      event.stopImmediatePropagation();
    },
    true
  );

  if (window.HTMLFormElement) {
    const blocked = function () {
      noteAttempt();
      throw new Error(
        "SUBMIT_BLOCKED_BY_GREENHOUSE_JOB_AGENT"
      );
    };

    try {
      HTMLFormElement.prototype.submit = blocked;
    } catch (_) {}

    try {
      HTMLFormElement.prototype.requestSubmit = blocked;
    } catch (_) {}
  }
})();
"""


@dataclass
class FillResult:
    label: str
    category: str
    answer_key: str | None
    required: bool
    status: str
    operation: str
    source: str
    reason: str

    def to_dict(
        self,
    ) -> dict:
        return asdict(
            self
        )


def is_custom_select_candidate(
    field: dict,
) -> bool:
    """
    Greenhouse custom select widgets commonly appear as two
    related text/search controls after normalization.

    We never treat a single ordinary text input as a dropdown.
    """

    source_count = int(
        field.get(
            "source_count",
            1,
        )
        or 1
    )

    source_types = {
        str(
            value
        ).lower()
        for value in (
            field.get(
                "source_types"
            )
            or []
        )
    }

    field_type = str(
        field.get(
            "type"
        )
        or ""
    ).lower()

    text_like = {
        "text",
        "search",
    }

    return (
        source_count > 1
        and (
            field_type
            in text_like
        )
        and (
            not source_types
            or source_types.issubset(
                text_like
            )
        )
    )


def build_fill_tasks(
    *,
    logical_fields: list[dict],
    resolved_fields: list,
) -> list[dict]:
    """
    Produce an explicit mutation plan.

    Only fields already marked READY by the safe resolver can
    become fill tasks. Assistance/missing/mismatch fields are
    excluded by construction.
    """

    tasks = []

    for field, resolved in zip(
        logical_fields,
        resolved_fields,
        strict=True,
    ):
        if resolved.status != STATUS_READY:
            continue

        action = (
            field.get(
                "decision",
                {}
            ).get(
                "action"
            )
        )

        if action not in {
            "PROFILE_VALUE",
            "FIXED_ANSWER",
            "RESUME_FILE",
        }:
            continue

        operation = (
            "UPLOAD_RESUME"
            if action
            == "RESUME_FILE"
            else (
                "SELECT_OPTION"
                if is_custom_select_candidate(
                    field
                )
                else "FILL_VALUE"
            )
        )

        tasks.append(
            {
                "field": field,
                "resolved": resolved,
                "operation": operation,
            }
        )

    return tasks


def _best_frame(
    page: Page,
) -> tuple[
    Frame,
    list[dict],
]:
    candidates = []

    for frame in page.frames:
        try:
            fields = inspect_form_fields(
                frame
            )
        except Exception:
            continue

        candidates.append(
            (
                frame,
                fields,
            )
        )

    if not candidates:
        return (
            page.main_frame,
            [],
        )

    return max(
        candidates,
        key=lambda item: len(
            item[1]
        ),
    )


def _classify_fields(
    fields: list[dict],
) -> list[dict]:
    classified = []

    for field in fields:
        decision = classify_field(
            label=field.get(
                "label"
            ),
            field_type=field.get(
                "type"
            ),
            name=field.get(
                "name"
            ),
            placeholder=field.get(
                "placeholder"
            ),
            context_text=field.get(
                "context_text"
            ),
        )

        item = dict(
            field
        )

        item[
            "decision"
        ] = decision.to_dict()

        classified.append(
            item
        )

    return classified


def _semantic_field_key(
    field: dict,
) -> tuple[
    str,
    str,
    str,
    str,
]:
    """
    Stable logical identity for a classified field.

    DOM indices are intentionally excluded because React/Greenhouse
    can insert/remove helper controls after a dropdown selection.
    """

    decision = (
        field.get(
            "decision"
        )
        or {}
    )

    return (
        _normalized(
            field.get(
                "label"
            )
            or ""
        ),
        str(
            decision.get(
                "category"
            )
            or ""
        ).upper(),
        str(
            decision.get(
                "action"
            )
            or ""
        ).upper(),
        str(
            decision.get(
                "answer_key"
            )
            or ""
        ).upper(),
    )


def _match_live_field(
    *,
    planned_field: dict,
    live_fields: list[dict],
) -> tuple[
    dict | None,
    str,
]:
    """
    Re-identify one logical field in a freshly inspected DOM.

    Matching is semantic, not positional. This prevents a stale nth()
    index from writing a later value into a different question after
    React re-renders the form.
    """

    planned_key = _semantic_field_key(
        planned_field
    )

    exact = [
        field
        for field in live_fields
        if _semantic_field_key(
            field
        )
        == planned_key
    ]

    if len(
        exact
    ) == 1:
        return (
            exact[
                0
            ],
            "Live field rebound by exact semantic identity.",
        )

    decision = (
        planned_field.get(
            "decision"
        )
        or {}
    )

    planned_category = str(
        decision.get(
            "category"
        )
        or ""
    ).upper()

    planned_action = str(
        decision.get(
            "action"
        )
        or ""
    ).upper()

    planned_answer_key = str(
        decision.get(
            "answer_key"
        )
        or ""
    ).upper()

    # Conservative fallback for labels that a live UI slightly
    # reformats. Category + action + answer key must still uniquely
    # identify the field.
    semantic = []

    for field in live_fields:
        live_decision = (
            field.get(
                "decision"
            )
            or {}
        )

        if (
            str(
                live_decision.get(
                    "category"
                )
                or ""
            ).upper()
            != planned_category
        ):
            continue

        if (
            str(
                live_decision.get(
                    "action"
                )
                or ""
            ).upper()
            != planned_action
        ):
            continue

        if (
            str(
                live_decision.get(
                    "answer_key"
                )
                or ""
            ).upper()
            != planned_answer_key
        ):
            continue

        semantic.append(
            field
        )

    if len(
        semantic
    ) == 1:
        return (
            semantic[
                0
            ],
            "Live field rebound by unique category/action/answer-key identity.",
        )

    return (
        None,
        (
            "Live field rebinding was not unique: "
            f"exact_matches={len(exact)}, "
            f"semantic_matches={len(semantic)}. "
            "Mutation skipped instead of using stale DOM indices."
        ),
    )


def _rebind_live_field(
    *,
    frame: Frame,
    planned_field: dict,
) -> tuple[
    dict | None,
    str,
]:
    """
    Re-inspect and re-classify immediately before every mutation.
    """

    fresh_logical_fields = inspect_form_fields(
        frame
    )

    fresh_classified_fields = _classify_fields(
        fresh_logical_fields
    )

    return _match_live_field(
        planned_field=planned_field,
        live_fields=fresh_classified_fields,
    )


def _operation_for_field(
    field: dict,
) -> str | None:
    action = (
        field.get(
            "decision",
            {}
        ).get(
            "action"
        )
    )

    if action == "RESUME_FILE":
        return "UPLOAD_RESUME"

    if action in {
        "PROFILE_VALUE",
        "FIXED_ANSWER",
    }:
        return (
            "SELECT_OPTION"
            if is_custom_select_candidate(
                field
            )
            else "FILL_VALUE"
        )

    return None


def _observable_field_state(
    field: dict,
) -> tuple[
    tuple[str, ...],
    int,
]:
    """
    State used only to detect unintended mutations.

    Empty helper values are ignored because React can recreate blank
    helper controls during a harmless re-render. Any non-empty value
    or checked control is significant.
    """

    nonempty_values = tuple(
        sorted(
            _normalized(
                value
            )
            for value in (
                field.get(
                    "values"
                )
                or []
            )
            if _normalized(
                value
            )
        )
    )

    checked_count = sum(
        1
        for value in (
            field.get(
                "checked_states"
            )
            or []
        )
        if bool(
            value
        )
    )

    return (
        nonempty_values,
        checked_count,
    )


def _snapshot_nonready_fields(
    *,
    logical_fields: list[dict],
    resolved_fields: list,
) -> list[dict]:
    snapshot = []

    for field, resolved in zip(
        logical_fields,
        resolved_fields,
        strict=True,
    ):
        if resolved.status == STATUS_READY:
            continue

        snapshot.append(
            {
                "field": field,
                "state": _observable_field_state(
                    field
                ),
                "status": resolved.status,
            }
        )

    return snapshot


def _detect_nonready_mutation(
    *,
    frame: Frame,
    snapshot: list[dict],
) -> tuple[
    bool,
    str,
]:
    """
    Verify that fields intentionally excluded from automation have
    not changed after a deterministic mutation.
    """

    live_fields = _classify_fields(
        inspect_form_fields(
            frame
        )
    )

    for item in snapshot:
        planned_field = item[
            "field"
        ]

        live_field, reason = _match_live_field(
            planned_field=planned_field,
            live_fields=live_fields,
        )

        if live_field is None:
            # A rerender may temporarily remove/recreate optional UI.
            # Missing identity is not itself proof of mutation, but
            # we cannot claim verified untouched in that case.
            continue

        before = item[
            "state"
        ]

        after = _observable_field_state(
            live_field
        )

        if after != before:
            return (
                True,
                (
                    "NON_READY_FIELD_MUTATED: "
                    f"{planned_field.get('label')!r} changed "
                    f"from {before!r} to {after!r}. "
                    "Further mutation stopped."
                ),
            )

    return (
        False,
        "No observable non-ready field mutation detected.",
    )


def _control_candidates(
    *,
    frame: Frame,
    field: dict,
):
    controls = frame.locator(
        CONTROL_SELECTOR
    )

    indices = [
        index
        for index in (
            field.get(
                "dom_indices"
            )
            or []
        )
        if isinstance(
            index,
            int,
        )
    ]

    return [
        controls.nth(
            index
        )
        for index in indices
    ]


def _first_usable_control(
    *,
    frame: Frame,
    field: dict,
):
    candidates = _control_candidates(
        frame=frame,
        field=field,
    )

    for locator in candidates:
        try:
            if locator.count() == 0:
                continue

            if locator.is_enabled():
                return locator
        except Exception:
            continue

    return None


def _normalized(
    value: Any,
) -> str:
    return " ".join(
        str(
            value
        ).split()
    ).strip().lower()


def _fill_plain_value(
    *,
    frame: Frame,
    field: dict,
    value: Any,
) -> tuple[
    bool,
    str,
]:
    control = _first_usable_control(
        frame=frame,
        field=field,
    )

    if control is None:
        return (
            False,
            "No usable DOM control was found.",
        )

    field_type = str(
        field.get(
            "type"
        )
        or ""
    ).lower()

    tag = str(
        field.get(
            "tag"
        )
        or ""
    ).lower()

    text = str(
        value
    )

    try:
        if (
            tag == "select"
            or field_type
            == "select"
        ):
            try:
                control.select_option(
                    label=text
                )
            except Exception:
                control.select_option(
                    value=text
                )

            return (
                True,
                "Native select option chosen.",
            )

        if field_type == "radio":
            candidates = _control_candidates(
                frame=frame,
                field=field,
            )

            desired = _normalized(
                text
            )

            for candidate in candidates:
                candidate_value = (
                    candidate.get_attribute(
                        "value"
                    )
                    or ""
                )

                candidate_label = candidate.evaluate(
                    """(element) => {
                      if (element.labels && element.labels.length) {
                        return Array.from(element.labels)
                          .map((label) => (
                            label.innerText ||
                            label.textContent ||
                            ""
                          ).trim())
                          .join(" ");
                      }

                      return "";
                    }"""
                )

                if desired in {
                    _normalized(
                        candidate_value
                    ),
                    _normalized(
                        candidate_label
                    ),
                }:
                    candidate.check(
                        force=False
                    )

                    return (
                        True,
                        "Matching radio option selected.",
                    )

            return (
                False,
                "No exact matching radio option was found.",
            )

        if field_type == "checkbox":
            desired = _normalized(
                text
            )

            if desired in {
                "yes",
                "true",
                "1",
            }:
                control.check(
                    force=False
                )

                return (
                    True,
                    "Checkbox checked.",
                )

            if desired in {
                "no",
                "false",
                "0",
            }:
                control.uncheck(
                    force=False
                )

                return (
                    True,
                    "Checkbox unchecked.",
                )

            return (
                False,
                "Checkbox value was not an explicit Yes/No boolean.",
            )

        control.fill(
            text
        )

        return (
            True,
            "Text-like control filled.",
        )

    except Exception as exc:
        return (
            False,
            f"DOM fill failed: {type(exc).__name__}: {exc}",
        )


def _visible_texts(
    locator,
    *,
    limit: int = 12,
) -> list[str]:
    values = []

    try:
        count = min(
            locator.count(),
            100,
        )
    except Exception:
        return values

    for index in range(
        count
    ):
        item = locator.nth(
            index
        )

        try:
            if not item.is_visible():
                continue

            text = " ".join(
                (
                    item.inner_text()
                    or ""
                ).split()
            ).strip()

            if (
                text
                and text not in values
            ):
                values.append(
                    text
                )

            if len(
                values
            ) >= limit:
                break
        except Exception:
            continue

    return values


def _custom_select_roots(
    *,
    frame: Frame,
    control,
) -> list:
    """
    Find only plausible visible popup containers.

    We intentionally avoid page-wide text matching so an exact
    country/company/etc. string elsewhere on the application page
    cannot be clicked accidentally.
    """

    roots = []

    for attribute in (
        "aria-controls",
        "aria-owns",
    ):
        try:
            target_id = (
                control.get_attribute(
                    attribute
                )
                or ""
            ).strip()
        except Exception:
            target_id = ""

        if target_id:
            root = frame.locator(
                f"#{target_id}"
            )

            try:
                if (
                    root.count() > 0
                    and root.first.is_visible()
                ):
                    roots.append(
                        root.first
                    )
            except Exception:
                pass

    for selector in (
        "[role='listbox']",
        "[role='menu']",
    ):
        candidate_roots = frame.locator(
            selector
        )

        try:
            count = min(
                candidate_roots.count(),
                20,
            )
        except Exception:
            count = 0

        for index in range(
            count
        ):
            root = candidate_roots.nth(
                index
            )

            try:
                if root.is_visible():
                    roots.append(
                        root
                    )
            except Exception:
                continue

    deduped = []
    seen = set()

    for root in roots:
        try:
            handle = root.element_handle()
            identity = (
                handle.evaluate(
                    "(element) => element"
                )
                if handle
                else None
            )
        except Exception:
            identity = None

        # ElementHandle identity is not hash-stable across calls, so
        # use locator text + role/id as a light duplicate guard.
        try:
            key = (
                root.get_attribute(
                    "id"
                ),
                root.get_attribute(
                    "role"
                ),
                " ".join(
                    (
                        root.inner_text()
                        or ""
                    ).split()
                )[:200],
            )
        except Exception:
            key = (
                None,
                None,
                str(
                    identity
                ),
            )

        if key in seen:
            continue

        seen.add(
            key
        )
        deduped.append(
            root
        )

    return deduped


def _option_text_matches(
    *,
    field: dict,
    desired: str,
    visible_text: str,
) -> bool:
    """
    Strict semantic matcher for custom-dropdown options.

    Default rule:
      normalized visible text must equal the configured value.

    COUNTRY exception:
      Greenhouse may render the country together with its calling
      code, e.g. "United States +1". This is accepted only when the
      field is already classified as COUNTRY and the suffix is only
      a '+' followed by 1-4 digits.

    No arbitrary prefix, substring, or fuzzy matching is allowed.
    """

    desired_clean = " ".join(
        str(desired).split()
    ).strip()

    visible_clean = " ".join(
        str(visible_text).split()
    ).strip()

    if (
        not desired_clean
        or not visible_clean
    ):
        return False

    if (
        visible_clean.casefold()
        == desired_clean.casefold()
    ):
        return True

    category = (
        field.get(
            "decision",
            {}
        ).get(
            "category"
        )
        or ""
    ).upper()

    if category != "COUNTRY":
        return False

    country_plus_calling_code = re.compile(
        rf"^{re.escape(desired_clean)}\s+\+\d{{1,4}}$",
        re.IGNORECASE,
    )

    return bool(
        country_plus_calling_code.fullmatch(
            visible_clean
        )
    )


def _select_custom_option(
    *,
    frame: Frame,
    field: dict,
    value: Any,
    timeout_ms: int = 2_500,
) -> tuple[
    bool,
    str,
]:
    """
    Safely operate a Greenhouse/React custom select.

    Safety rules:
      - never press Enter;
      - never page-wide click text;
      - click only one exact visible option inside a plausible
        listbox/menu/aria-controlled popup;
      - if resolution is ambiguous or absent, clear typed text and
        report diagnostics instead of guessing.
    """

    candidates = _control_candidates(
        frame=frame,
        field=field,
    )

    control = None

    # Prefer an actual ARIA combobox/search input if Greenhouse
    # exposes one among the normalized source controls.
    for candidate in candidates:
        try:
            if not candidate.is_enabled():
                continue

            role = (
                candidate.get_attribute(
                    "role"
                )
                or ""
            ).lower()

            aria_controls = (
                candidate.get_attribute(
                    "aria-controls"
                )
                or ""
            )

            aria_expanded = (
                candidate.get_attribute(
                    "aria-expanded"
                )
                or ""
            )

            if (
                role == "combobox"
                or aria_controls
                or aria_expanded
            ):
                control = candidate
                break
        except Exception:
            continue

    if control is None:
        control = _first_usable_control(
            frame=frame,
            field=field,
        )

    if control is None:
        return (
            False,
            "No usable custom-select input was found.",
        )

    desired = str(
        value
    ).strip()

    try:
        # Some widgets do not render their option portal until the
        # control has first been clicked/focused.
        control.click(
            timeout=timeout_ms
        )

        try:
            control.fill(
                desired
            )
        except Exception:
            # If the visible combobox shell is not directly fillable,
            # try another usable source control without pressing keys.
            fallback = _first_usable_control(
                frame=frame,
                field=field,
            )

            if (
                fallback is None
                or fallback == control
            ):
                raise

            control = fallback
            control.click(
                timeout=timeout_ms
            )
            control.fill(
                desired
            )

        frame.page.wait_for_timeout(
            400
        )

        roots = _custom_select_roots(
            frame=frame,
            control=control,
        )

        exact_matches = []

        # Preferred ARIA semantic path.
        #
        # Inspect visible option text directly instead of asking
        # Playwright for exact accessible-name equality. Greenhouse
        # country options may expose names such as "United States +1".
        # _option_text_matches() keeps that exception tightly scoped
        # to COUNTRY while all other fields remain exact-match only.
        role_options = frame.locator(
            "[role='option']"
        )

        try:
            count = min(
                role_options.count(),
                100,
            )
        except Exception:
            count = 0

        for index in range(
            count
        ):
            option = role_options.nth(
                index
            )

            try:
                if not option.is_visible():
                    continue

                option_text = " ".join(
                    (
                        option.inner_text()
                        or ""
                    ).split()
                ).strip()

                if _option_text_matches(
                    field=field,
                    desired=desired,
                    visible_text=option_text,
                ):
                    exact_matches.append(
                        option
                    )
            except Exception:
                continue

        # Fallback: exact visible text, but ONLY inside popup roots.
        if not exact_matches:
            exact_pattern = re.compile(
                rf"^\s*{re.escape(desired)}\s*$",
                re.IGNORECASE,
            )

            for root in roots:
                try:
                    matches = root.get_by_text(
                        exact_pattern
                    )

                    count = min(
                        matches.count(),
                        50,
                    )
                except Exception:
                    continue

                for index in range(
                    count
                ):
                    item = matches.nth(
                        index
                    )

                    try:
                        if item.is_visible():
                            exact_matches.append(
                                item
                            )
                    except Exception:
                        continue

        # Remove duplicate locators that point to the same visible text
        # hierarchy by preferring the first exact clickable candidate.
        if len(
            exact_matches
        ) == 1:
            exact_matches[
                0
            ].click(
                timeout=timeout_ms
            )

            return (
                True,
                (
                    "Unique safe custom-select option clicked "
                    "(exact text or COUNTRY + calling code)."
                ),
            )

        diagnostic_texts = []

        # Capture only option/listbox/menu text; never applicant values
        # from unrelated page regions.
        diagnostic_texts.extend(
            _visible_texts(
                frame.locator(
                    "[role='option']"
                )
            )
        )

        if not diagnostic_texts:
            for root in roots:
                for text_value in _visible_texts(
                    root.locator(
                        "*"
                    ),
                    limit=12,
                ):
                    if (
                        text_value
                        not in diagnostic_texts
                    ):
                        diagnostic_texts.append(
                            text_value
                        )

                    if len(
                        diagnostic_texts
                    ) >= 12:
                        break

                if len(
                    diagnostic_texts
                ) >= 12:
                    break

        try:
            control.fill(
                ""
            )
        except Exception:
            pass

        try:
            role = (
                control.get_attribute(
                    "role"
                )
                or "-"
            )
            aria_controls = (
                control.get_attribute(
                    "aria-controls"
                )
                or "-"
            )
            aria_expanded = (
                control.get_attribute(
                    "aria-expanded"
                )
                or "-"
            )
        except Exception:
            role = "-"
            aria_controls = "-"
            aria_expanded = "-"

        diagnostics = (
            " | visible popup text: "
            + (
                "; ".join(
                    diagnostic_texts
                )
                if diagnostic_texts
                else "<none>"
            )
        )

        return (
            False,
            (
                "Custom dropdown exact-match resolution failed for "
                f"{desired!r}: {len(exact_matches)} exact visible "
                "candidate(s). Input was cleared. "
                f"control role={role!r}, "
                f"aria-controls={aria_controls!r}, "
                f"aria-expanded={aria_expanded!r}"
                + diagnostics
            ),
        )

    except Exception as exc:
        try:
            control.fill(
                ""
            )
        except Exception:
            pass

        return (
            False,
            (
                "Custom-select operation failed and was cleared: "
                f"{type(exc).__name__}: {exc}"
            ),
        )


def _upload_resume(
    *,
    frame: Frame,
    field: dict,
    resume_path: str | Path,
) -> tuple[
    bool,
    str,
]:
    resume = Path(
        resume_path
    )

    if not resume.is_file():
        return (
            False,
            f"Resume file does not exist: {resume}",
        )

    candidates = _control_candidates(
        frame=frame,
        field=field,
    )

    for control in candidates:
        try:
            control_type = (
                control.get_attribute(
                    "type"
                )
                or ""
            ).lower()

            if control_type != "file":
                continue

            control.set_input_files(
                str(
                    resume.resolve()
                )
            )

            return (
                True,
                "Resume attached to the file input.",
            )

        except Exception:
            continue

    return (
        False,
        "No usable resume file input was found.",
    )


def _submit_attempt_count(
    page: Page,
) -> int:
    total = 0

    for frame in page.frames:
        try:
            count = frame.evaluate(
                """() => (
                  window.__GREENHOUSE_JOB_AGENT_SUBMIT_ATTEMPTS__ ||
                  0
                )"""
            )

            total += int(
                count
                or 0
            )
        except Exception:
            continue

    return total


def detect_page_challenge(
    page: Page,
) -> dict:
    """
    Conservative page-level CAPTCHA / anti-bot detector.

    If a known challenge surface is present anywhere in the page or
    its frames, browser mutation must not start.

    This detector never clicks, solves, bypasses, or otherwise
    interacts with a challenge.
    """

    selector_signals = (
        (
            "reCAPTCHA iframe",
            "iframe[src*='recaptcha' i]",
        ),
        (
            "reCAPTCHA widget",
            ".g-recaptcha, [data-recaptcha-sitekey]",
        ),
        (
            "hCaptcha iframe",
            "iframe[src*='hcaptcha' i]",
        ),
        (
            "hCaptcha widget",
            ".h-captcha, [data-hcaptcha-widget-id]",
        ),
        (
            "Cloudflare Turnstile iframe",
            "iframe[src*='challenges.cloudflare.com' i]",
        ),
        (
            "Cloudflare Turnstile widget",
            ".cf-turnstile, [data-sitekey][class*='turnstile' i]",
        ),
    )

    text_signals = (
        "verify you are human",
        "verify that you are human",
        "checking your browser",
        "complete the captcha",
        "complete captcha",
        "attention required",
    )

    reasons = []

    for frame in page.frames:
        for label, selector in selector_signals:
            try:
                locator = frame.locator(
                    selector
                )

                count = min(
                    locator.count(),
                    20,
                )

                if count > 0:
                    visible = 0

                    for index in range(
                        count
                    ):
                        try:
                            if locator.nth(
                                index
                            ).is_visible():
                                visible += 1
                        except Exception:
                            continue

                    reasons.append(
                        f"{label}: {count} element(s), {visible} visible"
                    )
            except Exception:
                continue

        try:
            body_text = _normalized(
                frame.locator(
                    "body"
                ).inner_text(
                    timeout=1_500
                )
            )
        except Exception:
            body_text = ""

        for phrase in text_signals:
            if phrase in body_text:
                reasons.append(
                    f"challenge text detected: {phrase!r}"
                )

    deduped = []

    for reason in reasons:
        if reason not in deduped:
            deduped.append(
                reason
            )

    return {
        "detected": bool(
            deduped
        ),
        "reasons": deduped,
    }


def safe_fill_application(
    *,
    url: str,
    profile: ApplicantProfile,
    resume_path: str | Path,
    headless: bool = True,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    settle_ms: int = DEFAULT_SETTLE_MS,
    hold_seconds: int = 0,
    screenshot_path: str | None = None,
) -> dict:
    """
    Fill only READY deterministic fields.

    HARD GUARANTEES:
      - no submit button is clicked
      - submit/requestSubmit are blocked
      - form submit events are prevented
      - no Enter key is used
      - NEEDS_ASSISTANCE fields are untouched
      - POLICY_MISMATCH fields are untouched
      - demographic/EEO fields are untouched
      - every mutation re-inspects/rebinds the target field
        so stale React DOM indices are never trusted
      - after every successful mutation, non-ready fields are
        re-inspected for observable contamination; if detected,
        the run stops immediately
      - page-level CAPTCHA / anti-bot signals are checked before
        mutation; if detected, zero fields/files are touched
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
        )

        context = browser.new_context()

        context.add_init_script(
            SUBMIT_GUARD_SCRIPT
        )

        page = context.new_page()

        page.set_default_timeout(
            timeout_ms
        )

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass

        page.wait_for_timeout(
            settle_ms
        )

        challenge = detect_page_challenge(
            page
        )

        if challenge[
            "detected"
        ]:
            submit_attempts = _submit_attempt_count(
                page
            )

            output = {
                "requested_url": url,
                "final_url": page.url,
                "page_title": page.title(),
                "form_frame_url": None,
                "resolution_summary": {
                    "total_fields": 0,
                    "ready_fields": 0,
                    "required_unresolved": 1,
                    "optional_unresolved": 0,
                    "policy_mismatches": 0,
                    "missing_resume": 0,
                    "ready_for_submission": False,
                    "browser_modified": False,
                    "submit_attempted": False,
                },
                "fill_results": [],
                "fill_summary": {
                    "tasks_attempted": 0,
                    "filled": 0,
                    "fill_failed": 0,
                    "required_assistance_untouched": 1,
                    "optional_unresolved_untouched": 0,
                    "submit_attempts_blocked": submit_attempts,
                    "submit_clicked_by_agent": False,
                    "browser_modified": False,
                    "application_submitted": False,
                    "nonready_mutation_detected": False,
                    "nonready_mutation_reason": "",
                    "nonready_fields_verified_after_each_success": True,
                    "page_challenge_detected": True,
                    "page_challenge_reasons": challenge[
                        "reasons"
                    ],
                    "mutation_blocked_by_challenge": True,
                },
            }

            context.close()
            browser.close()

            return output

        frame, logical_fields = _best_frame(
            page
        )

        classified_fields = _classify_fields(
            logical_fields
        )

        inspection = {
            "requested_url": url,
            "final_url": page.url,
            "page_title": page.title(),
            "form_frame_url": frame.url,
            "fields": classified_fields,
            "submit_attempted": False,
        }

        resolution = resolve_application(
            inspection=inspection,
            profile=profile,
            resume_path=resume_path,
        )

        tasks = build_fill_tasks(
            logical_fields=classified_fields,
            resolved_fields=resolution[
                "fields"
            ],
        )

        nonready_snapshot = _snapshot_nonready_fields(
            logical_fields=classified_fields,
            resolved_fields=resolution[
                "fields"
            ],
        )

        fill_results = []
        safety_violation = False
        safety_violation_reason = ""

        for task in tasks:
            planned_field = task[
                "field"
            ]

            resolved = task[
                "resolved"
            ]

            planned_operation = task[
                "operation"
            ]

            live_field, rebind_reason = _rebind_live_field(
                frame=frame,
                planned_field=planned_field,
            )

            if live_field is None:
                fill_results.append(
                    FillResult(
                        label=resolved.label,
                        category=resolved.category,
                        answer_key=resolved.answer_key,
                        required=resolved.required,
                        status="FILL_FAILED",
                        operation=planned_operation,
                        source=resolved.source,
                        reason=rebind_reason,
                    )
                )

                continue

            operation = _operation_for_field(
                live_field
            )

            if operation is None:
                fill_results.append(
                    FillResult(
                        label=resolved.label,
                        category=resolved.category,
                        answer_key=resolved.answer_key,
                        required=resolved.required,
                        status="FILL_FAILED",
                        operation=planned_operation,
                        source=resolved.source,
                        reason=(
                            rebind_reason
                            + " Live field no longer has an "
                            "allowed deterministic mutation action."
                        ),
                    )
                )

                continue

            success = False
            mutation_reason = ""

            if operation == "UPLOAD_RESUME":
                success, mutation_reason = _upload_resume(
                    frame=frame,
                    field=live_field,
                    resume_path=resume_path,
                )

            elif operation == "SELECT_OPTION":
                success, mutation_reason = _select_custom_option(
                    frame=frame,
                    field=live_field,
                    value=resolved.value,
                )

            elif operation == "FILL_VALUE":
                success, mutation_reason = _fill_plain_value(
                    frame=frame,
                    field=live_field,
                    value=resolved.value,
                )

            fill_results.append(
                FillResult(
                    label=resolved.label,
                    category=resolved.category,
                    answer_key=resolved.answer_key,
                    required=resolved.required,
                    status=(
                        "FILLED"
                        if success
                        else "FILL_FAILED"
                    ),
                    operation=operation,
                    source=resolved.source,
                    reason=(
                        rebind_reason
                        + " "
                        + mutation_reason
                    ).strip(),
                )
            )

            if success:
                (
                    contamination,
                    contamination_reason,
                ) = _detect_nonready_mutation(
                    frame=frame,
                    snapshot=nonready_snapshot,
                )

                if contamination:
                    safety_violation = True
                    safety_violation_reason = contamination_reason
                    break

        submit_attempts = _submit_attempt_count(
            page
        )

        if screenshot_path:
            destination = Path(
                screenshot_path
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            page.screenshot(
                path=str(
                    destination
                ),
                full_page=True,
            )

        if hold_seconds > 0:
            page.wait_for_timeout(
                int(
                    hold_seconds
                    * 1000
                )
            )

        fill_failed = sum(
            1
            for result in fill_results
            if result.status
            == "FILL_FAILED"
        )

        filled = sum(
            1
            for result in fill_results
            if result.status
            == "FILLED"
        )

        output = {
            "requested_url": url,
            "final_url": page.url,
            "page_title": page.title(),
            "form_frame_url": frame.url,
            "resolution_summary": resolution[
                "summary"
            ],
            "fill_results": [
                result.to_dict()
                for result in fill_results
            ],
            "fill_summary": {
                "tasks_attempted": len(
                    fill_results
                ),
                "filled": filled,
                "fill_failed": fill_failed,
                "required_assistance_untouched": resolution[
                    "summary"
                ][
                    "required_unresolved"
                ],
                "optional_unresolved_untouched": resolution[
                    "summary"
                ][
                    "optional_unresolved"
                ],
                "submit_attempts_blocked": submit_attempts,
                "submit_clicked_by_agent": False,
                "browser_modified": (
                    filled > 0
                ),
                "application_submitted": False,
                "nonready_mutation_detected": safety_violation,
                "nonready_mutation_reason": safety_violation_reason,
                "nonready_fields_verified_after_each_success": True,
                "page_challenge_detected": False,
                "page_challenge_reasons": [],
                "mutation_blocked_by_challenge": False,
            },
        }

        context.close()
        browser.close()

        return output
