# Supabase Browser Handoff Integration V1.1

This milestone connects Browser Assistance Handoff V1 to the existing
`applications` + `assistance_requests` repository flow.

It does not weaken RLS, expose the Supabase secret key, open a browser,
solve CAPTCHA, or submit an application.

## What is added

- `sanitize_browser_handoff()`
- compact `BROWSER:` assistance reasons
- `JobRepository.find_job_id()`
- `JobRepository.sync_browser_assistance_handoff()`
- one unresolved `source='BROWSER'` request per application
- structured redacted handoff JSON
- automatic resolution when a later packet becomes `AGENT_CONTINUE`
- protection against clearing `ELIGIBILITY:` assistance
- protection against resetting progressed application statuses

## Database migration

Run this migration in Supabase before using the new repository method:

```text
migrations/20260904_browser_assistance_handoff_v1.sql
```

The migration only extends `assistance_requests`; it does not alter RLS.

## Local regression

```bash
python -u test_browser_handoff_repository.py
```

## Robinhood production persistence

After the migration and after the local regression passes:

```bash
python -u persist_browser_handoff.py   browser_runs/v15/robinhood_handoff_v1.json   --board-token robinhood   --greenhouse-job-id 8088444
```

Expected route for the validated Robinhood packet:

```text
Route:                 NEEDS_ASSISTANCE
Challenge detected:    YES
Deterministic ready:   11
Required human fields: 10
Selected resume:       Software_Engineer.pdf
Profile values stored: NO
Browser opened:        NO
Application submitted: NO
```

Keep `browser_runs/` private/ignored.


## V1.1 route guard

Browser handoff persistence now fails closed unless the newest completed
`job_evaluations.route` for the job is exactly `AGENT_APPLY`.

This prevents manually selected `MANUAL_PRIORITY` jobs from being converted
into Browser Agent assistance records simply because a developer ran the
browser CLI against them.

For a `MANUAL_PRIORITY` job, `persist_browser_handoff.py` should print a
routing-guard error and perform no database mutation.

The validated Robinhood job `8088444` is `MANUAL_PRIORITY`, so re-running
the persistence CLI with V1.1 should now be blocked. Existing test data
created by V1 remains historical and does not need to be manually edited.
