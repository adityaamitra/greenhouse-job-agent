from pathlib import Path

from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from src.browser.field_classifier import classify_field
from src.browser.greenhouse_form import inspect_form_fields


DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_SETTLE_MS = 1_500


def _inspect_best_frame(page) -> tuple[str, list[dict]]:
    candidates = []

    for frame in page.frames:
        try:
            fields = inspect_form_fields(frame)
        except Exception:
            continue

        candidates.append(
            (
                frame.url,
                fields,
            )
        )

    if not candidates:
        return (
            page.url,
            [],
        )

    return max(
        candidates,
        key=lambda item: len(item[1]),
    )


def inspect_application(
    *,
    url: str,
    headless: bool = True,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    settle_ms: int = DEFAULT_SETTLE_MS,
    screenshot_path: str | None = None,
) -> dict:
    """
    Browser Application Agent V1.2 remains read-only:
      - no values entered
      - no radio/checkbox changes
      - no file uploads
      - no submit clicks
    """

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
        )

        context = browser.new_context()
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

        (
            form_frame_url,
            fields,
        ) = _inspect_best_frame(page)

        classified_fields = []

        for field in fields:
            decision = classify_field(
                label=field.get("label"),
                field_type=field.get("type"),
                name=field.get("name"),
                placeholder=field.get("placeholder"),
                context_text=field.get("context_text"),
            )

            item = dict(field)
            item["decision"] = decision.to_dict()
            classified_fields.append(item)

        if screenshot_path:
            destination = Path(
                screenshot_path
            )
            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            page.screenshot(
                path=str(destination),
                full_page=True,
            )

        result = {
            "requested_url": url,
            "final_url": page.url,
            "page_title": page.title(),
            "form_frame_url": form_frame_url,
            "fields": classified_fields,
            "submit_attempted": False,
        }

        context.close()
        browser.close()

        return result
