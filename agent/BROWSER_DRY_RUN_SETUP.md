# Safe Dry-Run Autofill V1.5

This milestone **does modify application form fields**, but it never submits the form.

Hard safety rules:

- only resolver fields with status `READY` are touched;
- `NEEDS_ASSISTANCE`, missing-profile, and policy-mismatch fields are untouched;
- no submit button is clicked;
- `HTMLFormElement.submit()` and `requestSubmit()` are blocked;
- `submit` events are prevented;
- the filler never presses Enter;
- CAPTCHA/anti-bot controls are not bypassed;
- custom dropdowns require one exact visible option; otherwise the typed value is cleared;
- screenshots are optional because a post-fill screenshot can contain PII.

Before using this milestone, keep these local artifacts out of Git:

```gitignore
agent/config/applicant_profile.json
agent/browser_runs/
```

If `.gitignore` is inside `agent/`, use:

```gitignore
config/applicant_profile.json
browser_runs/
```

Run the synthetic safety test:

```bash
python -u test_safe_form_filler.py
```

First real Glean run, visibly in Chromium:

```bash
python -u dry_run_fill_application.py   "https://job-boards.greenhouse.io/gleanwork/jobs/4006734005"   --profile config/applicant_profile.json   --resume "resumes/Fullstack_Engineer.pdf"   --headed   --hold-seconds 20   --json browser_runs/v15/glean_fill_v1.json
```

Do not add `--screenshot` unless you intentionally want a private local image that can contain personal information.

## V1.5 custom-dropdown diagnostics

V1.5 keeps exact-match-only dropdown selection but improves Greenhouse custom-select handling:

- clicks/focuses the combobox before typing;
- prefers ARIA combobox controls;
- searches exact options inside listbox/menu/aria-controlled popups;
- never presses Enter;
- never performs page-wide text clicking;
- clears the input if no single exact option can be resolved;
- reports visible popup text and ARIA metadata when selection fails.

This is intentionally conservative. A failed Country dropdown is safer than guessing a nearby option.

## V1.5 country-option rule

Greenhouse can render a country option together with its telephone
calling code, for example:

```text
United States +1
```

V1.5 accepts that representation only for a field already classified
as `COUNTRY`, and only when the suffix is exactly a `+` calling code.
Other dropdown categories remain strict exact-text matches.

## V1.5 live-field rebinding

A real Glean test demonstrated that selecting Country can cause the
React form to insert/remove helper controls. That makes previously
captured `dom_indices` stale.

V1.5 therefore treats DOM indices as short-lived implementation details:

- the form is re-inspected immediately before every mutation;
- the target is re-classified and rebound by label/category/action/answer-key;
- fresh DOM indices are used only after that semantic rebinding;
- ambiguous or missing rebinding causes `FILL_FAILED`;
- the filler never falls back to a stale positional index.

This prevents a later profile value from being written into a neighboring
`NEEDS_ASSISTANCE` question after a React re-render.

## V1.5 non-ready contamination verification

A previous real Glean run showed that a stale DOM index could put the
portfolio URL into the required hybrid-policy question. The old summary
still said assistance fields were untouched because it only counted the
resolver plan.

V1.5 adds an actual runtime verification layer:

- snapshot all non-READY field observable states before filling;
- after every successful deterministic mutation, re-inspect the live form;
- compare non-empty values / checked states for non-READY fields;
- if any non-READY field changed, set `nonready_mutation_detected = true`
  and stop further mutations immediately.

This check supplements semantic live-field rebinding; it does not replace it.

## V1.5 page-level CAPTCHA / anti-bot gate

Before any field fill or resume upload, V1.5 scans the page and its frames
for common challenge surfaces, including reCAPTCHA, hCaptcha, Cloudflare
Turnstile, and common human-verification text.

If a challenge is detected:

- no profile field is filled;
- no resume is uploaded;
- no challenge is clicked or solved;
- the run reports `mutation_blocked_by_challenge = true`;
- the application remains unsubmitted.

This is intentionally conservative. A false positive should route to human
assistance rather than risk bypassing an anti-bot control.
