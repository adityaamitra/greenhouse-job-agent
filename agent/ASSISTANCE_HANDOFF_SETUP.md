# Browser Assistance Handoff V1

This milestone converts a Greenhouse inspection + safe resolver output
into a compact human handoff packet.

It does **not** open a browser, fill a field, upload a file, solve a CAPTCHA,
or submit an application.

## Inputs

- inspection JSON from `inspect_application_form.py`
- private applicant profile
- selected resume path
- optional fill report from `dry_run_fill_application.py`

## Outputs

- terminal Markdown-style packet
- optional JSON packet
- optional Markdown file

PII profile values are not printed. Only fixed policy answers such as
work authorization / sponsorship may be shown as Yes/No.

## Example

```bash
python -u generate_assistance_handoff.py   browser_runs/v15/robinhood.json   --profile config/applicant_profile.json   --resume "resumes/Software_Engineer.pdf"   --fill-report browser_runs/v15/robinhood_fill_v15.json   --json browser_runs/v15/robinhood_handoff_v1.json   --markdown browser_runs/v15/robinhood_handoff_v1.md
```

Keep `browser_runs/` private/ignored because application artifacts can contain
sensitive workflow details.
