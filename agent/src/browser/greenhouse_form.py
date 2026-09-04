from collections import OrderedDict
import re


DOM_FIELD_SCRIPT = r"""
() => {
  const clean = (value) => String(value || "")
    .replace(/\s+/g, " ")
    .trim();

  const shortText = (value, maxLength = 900) => {
    const text = clean(value);
    return text.length <= maxLength
      ? text
      : text.slice(0, maxLength);
  };

  const isTechnical = (element) => {
    const signature = [
      element.getAttribute("name"),
      element.getAttribute("id"),
      element.getAttribute("class"),
      element.getAttribute("aria-label"),
    ]
      .map((value) => clean(value).toLowerCase())
      .join(" ");

    return (
      signature.includes("recaptcha") ||
      signature.includes("captcha") ||
      signature.includes("cf-turnstile") ||
      signature.includes("turnstile-response")
    );
  };

  const isVisible = (element) => {
    const style = window.getComputedStyle(element);

    if (
      style.display === "none" ||
      style.visibility === "hidden" ||
      style.visibility === "collapse"
    ) {
      return false;
    }

    const rect = element.getBoundingClientRect();

    return (
      rect.width > 0 ||
      rect.height > 0 ||
      element.getClientRects().length > 0
    );
  };

  const associatedLabel = (element) => {
    if (element.labels && element.labels.length > 0) {
      const text = Array.from(element.labels)
        .map((label) => clean(label.innerText || label.textContent))
        .filter(Boolean)
        .join(" ");

      if (text) {
        return shortText(text);
      }
    }

    const id = element.getAttribute("id");

    if (id) {
      const escaped = (
        window.CSS && CSS.escape
          ? CSS.escape(id)
          : id.replace(/"/g, '\\"')
      );

      const explicit = document.querySelector(
        `label[for="${escaped}"]`
      );

      if (explicit) {
        const text = clean(
          explicit.innerText || explicit.textContent
        );

        if (text) {
          return shortText(text);
        }
      }
    }

    return "";
  };

  const textFromIds = (ids) => {
    if (!ids) {
      return "";
    }

    return shortText(
      ids
        .split(/\s+/)
        .map((id) => document.getElementById(id))
        .filter(Boolean)
        .map((node) => clean(node.innerText || node.textContent))
        .filter(Boolean)
        .join(" ")
    );
  };

  const nearestContext = (element) => {
    let node = element.parentElement;
    let depth = 0;
    let best = "";

    while (node && depth < 10) {
      if (
        node.tagName === "BODY" ||
        node.tagName === "HTML"
      ) {
        break;
      }

      const text = clean(
        node.innerText || node.textContent
      );

      if (
        text &&
        text.length <= 1800
      ) {
        best = text;

        const lower = text.toLowerCase();

        if (
          lower.includes("resume") ||
          lower.includes("cover letter") ||
          lower.includes("authorized") ||
          lower.includes("eligible to work") ||
          lower.includes("sponsorship") ||
          lower.includes("immigration support") ||
          lower.includes("veteran") ||
          lower.includes("disability") ||
          lower.includes("race") ||
          lower.includes("ethnicity") ||
          lower.includes("gender") ||
          lower.includes("sexual orientation") ||
          lower.includes("non-compete") ||
          lower.includes("non-solicitation")
        ) {
          return shortText(text, 1400);
        }
      }

      node = node.parentElement;
      depth += 1;
    }

    return shortText(best, 1400);
  };

  const questionFromAncestors = (element) => {
    let node = element.parentElement;
    let depth = 0;

    while (node && depth < 10) {
      if (
        node.tagName === "FORM" ||
        node.tagName === "BODY" ||
        node.tagName === "HTML"
      ) {
        break;
      }

      const candidates = Array.from(
        node.querySelectorAll(
          [
            "legend",
            "label",
            "[data-testid*='question']",
            "[data-testid*='label']",
            "[class*='question']",
            "[class*='label']",
            "h1",
            "h2",
            "h3",
            "h4",
          ].join(", ")
        )
      );

      for (const candidate of candidates) {
        const text = clean(
          candidate.innerText || candidate.textContent
        );

        if (
          text &&
          text.length <= 900
        ) {
          return text;
        }
      }

      node = node.parentElement;
      depth += 1;
    }

    return "";
  };

  const controls = Array.from(
    document.querySelectorAll(
      "input, select, textarea"
    )
  );

  const result = [];

  controls.forEach((element, index) => {
    const tag = element.tagName.toLowerCase();

    const type = (
      tag === "input"
        ? (element.getAttribute("type") || "text")
        : tag
    ).toLowerCase();

    if (
      [
        "hidden",
        "submit",
        "button",
        "reset",
        "image",
      ].includes(type)
    ) {
      return;
    }

    if (
      element.disabled ||
      isTechnical(element)
    ) {
      return;
    }

    if (
      ![
        "file",
        "radio",
        "checkbox",
      ].includes(type)
      && !isVisible(element)
    ) {
      return;
    }

    const optionLabel = associatedLabel(element);

    const ariaLabel = clean(
      element.getAttribute("aria-label")
    );

    const labelledBy = textFromIds(
      element.getAttribute("aria-labelledby")
    );

    const placeholder = clean(
      element.getAttribute("placeholder")
    );

    const ancestorQuestion = questionFromAncestors(
      element
    );

    const contextText = nearestContext(
      element
    );

    const questionLabel = (
      optionLabel ||
      labelledBy ||
      ariaLabel ||
      placeholder ||
      ancestorQuestion ||
      clean(element.getAttribute("name")) ||
      clean(element.getAttribute("id"))
    );

    let options = [];

    if (tag === "select") {
      options = Array.from(element.options || [])
        .map((option) => clean(option.textContent))
        .filter(Boolean);
    }

    result.push({
      index,
      tag,
      type,
      id: clean(element.getAttribute("id")),
      name: clean(element.getAttribute("name")),
      label: shortText(questionLabel),
      option_label: shortText(optionLabel),
      placeholder: shortText(placeholder),
      context_text: shortText(contextText, 1400),
      required: Boolean(
        element.required ||
        element.getAttribute("aria-required") === "true"
      ),
      value: (
        type === "file"
          ? ""
          : shortText(element.value || "", 250)
      ),
      checked: (
        type === "checkbox" ||
        type === "radio"
          ? Boolean(element.checked)
          : false
      ),
      options,
    });
  });

  return result;
}
"""


TYPE_PRIORITY = {
    "file": 100,
    "textarea": 95,
    "select": 90,
    "radio": 85,
    "checkbox": 85,
    "tel": 80,
    "email": 75,
    "url": 70,
    "text": 60,
    "search": 50,
}


def _normalize(value: str | None) -> str:
    text = (value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _technical(field: dict) -> bool:
    signature = " ".join(
        str(field.get(key) or "").lower()
        for key in (
            "name",
            "id",
            "label",
            "context_text",
        )
    )

    return any(
        token in signature
        for token in (
            "recaptcha",
            "captcha",
            "cf-turnstile",
            "turnstile-response",
        )
    )


def _file_semantic_key(field: dict) -> str:
    combined = _normalize(
        " ".join(
            [
                str(field.get("label") or ""),
                str(field.get("context_text") or ""),
            ]
        )
    )

    if (
        "resume" in combined
        or "curriculum vitae" in combined
        or "resume cv" in combined
    ):
        return "resume"

    if "cover letter" in combined:
        return "cover_letter"

    return (
        "unknown_"
        + str(field.get("index"))
    )


def _group_key(field: dict) -> str:
    field_type = (field.get("type") or "").lower()
    name = field.get("name") or ""
    label = _normalize(field.get("label"))

    if field_type == "file":
        return (
            "file:"
            + _file_semantic_key(field)
        )

    if (
        field_type in {
            "radio",
            "checkbox",
        }
        and name
    ):
        return (
            f"group:{field_type}:{name}"
        )

    if name:
        return f"named:{name}"

    if label:
        return f"field:{label}"

    return f"single:{field.get('index')}"


def _merge_options(
    target: list[str],
    additions: list[str],
) -> None:
    for option in additions:
        if option and option not in target:
            target.append(option)


def _new_group(field: dict) -> dict:
    return {
        "tag": field.get("tag"),
        "type": field.get("type"),
        "name": field.get("name"),
        "id": field.get("id"),
        "label": field.get("label"),
        "placeholder": field.get("placeholder"),
        "context_text": field.get("context_text"),
        "required": bool(field.get("required")),
        "options": list(field.get("options") or []),
        "values": [field.get("value") or ""],
        "checked_states": [bool(field.get("checked"))],
        "dom_indices": [field.get("index")],
        "source_types": [field.get("type")],
        "source_count": 1,
    }


def _looks_like_helper(
    field: dict,
    previous: dict | None,
) -> bool:
    """
    Detect Greenhouse custom-select helper inputs.

    We only merge when the helper is unlabeled AND its local
    context clearly contains the preceding logical field label.
    This avoids blindly discarding genuine unlabeled fields.
    """

    if previous is None:
        return False

    if _normalize(field.get("label")):
        return False

    if field.get("name") or field.get("placeholder"):
        return False

    if (field.get("type") or "").lower() not in {
        "text",
        "search",
    }:
        return False

    previous_label = _normalize(
        previous.get("label")
    )

    context = _normalize(
        field.get("context_text")
    )

    if not previous_label or not context:
        return False

    return (
        previous_label in context
        or context in previous_label
    )


def group_fields(raw_fields: list[dict]) -> list[dict]:
    """
    Normalize raw Greenhouse/React DOM controls into logical
    application fields.
    """

    grouped = OrderedDict()
    last_key = None

    for field in raw_fields:
        field_type = (
            field.get("type") or ""
        ).lower()

        if (
            field_type in {
                "hidden",
                "submit",
                "button",
                "reset",
                "image",
            }
            or _technical(field)
        ):
            continue

        previous = (
            grouped.get(last_key)
            if last_key is not None
            else None
        )

        if _looks_like_helper(
            field,
            previous,
        ):
            previous["source_count"] += 1
            previous["dom_indices"].append(
                field.get("index")
            )

            if (
                field_type
                not in previous["source_types"]
            ):
                previous["source_types"].append(
                    field_type
                )

            previous.setdefault(
                "values",
                [],
            ).append(
                field.get(
                    "value"
                )
                or ""
            )

            previous.setdefault(
                "checked_states",
                [],
            ).append(
                bool(
                    field.get(
                        "checked"
                    )
                )
            )

            continue

        key = _group_key(field)

        if key not in grouped:
            grouped[key] = _new_group(
                field
            )
        else:
            group = grouped[key]
            group["source_count"] += 1
            group["dom_indices"].append(
                field.get("index")
            )
            group["required"] = (
                group["required"]
                or bool(field.get("required"))
            )

            if field_type not in group["source_types"]:
                group["source_types"].append(
                    field_type
                )

            _merge_options(
                group["options"],
                list(field.get("options") or []),
            )

            group.setdefault(
                "values",
                [],
            ).append(
                field.get("value")
                or ""
            )

            group.setdefault(
                "checked_states",
                [],
            ).append(
                bool(
                    field.get(
                        "checked"
                    )
                )
            )

            if (
                TYPE_PRIORITY.get(field_type, 0)
                > TYPE_PRIORITY.get(
                    group["type"],
                    0,
                )
            ):
                group["type"] = field_type
                group["tag"] = field.get("tag")

            if (
                len(field.get("context_text") or "")
                > len(group.get("context_text") or "")
            ):
                group["context_text"] = (
                    field.get("context_text")
                )

        last_key = key

    return list(grouped.values())


def inspect_form_fields(page_or_frame) -> list[dict]:
    raw_fields = page_or_frame.evaluate(
        DOM_FIELD_SCRIPT
    )

    return group_fields(
        raw_fields
    )
