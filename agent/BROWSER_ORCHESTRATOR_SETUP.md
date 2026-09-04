# Browser Orchestrator V1

Browser Orchestrator V1 replaces the manual browser-agent command chain
with one fail-closed command for a tracked `AGENT_APPLY` Greenhouse job.

It still has **NO application submit path**.

## Production sequence

1. Resolve the tracked job from `board_token + greenhouse_job_id`.
2. Require:
   - active job
   - latest matcher route = `AGENT_APPLY`
   - application method = `AGENT`
   - status = `PENDING` or `IN_PROGRESS`
   - no eligibility/non-browser assistance already active
   - matcher-selected resume metadata exists
3. Resolve the selected resume from `resumes/`.
4. Perform a fresh read-only Greenhouse inspection.
5. Re-check the route/application state immediately before mutation.
6. Run Safe Dry-Run Autofill V1.5.
   - CAPTCHA/anti-bot challenge => zero mutations.
   - assistance fields stay untouched.
   - no Enter key.
   - no submit.
7. Generate Browser Assistance Handoff V1.
   - browser fill failures now become explicit assistance items.
8. Persist the sanitized handoff through Supabase Browser Handoff V1.1.
   - the repository route guard runs again immediately before the write.
9. Write redacted local artifacts under `browser_runs/orchestrator/`.

## Files added/updated

- `src/browser/orchestrator.py`
- `run_browser_application.py`
- `test_browser_orchestrator.py`
- updated `src/browser/assistance_handoff.py`
- updated `src/database/repository.py`

Keep your existing private `src/database/supabase_client.py`.
This bundle intentionally does not include or request any Supabase secret.

## Regression

```bash
python -u test_browser_orchestrator.py
```

## First real smoke test

Choose a job whose latest matcher route is actually `AGENT_APPLY`.

Start without a database handoff write:

```bash
python -u run_browser_application.py \
  --board-token <board_token> \
  --greenhouse-job-id <greenhouse_job_id> \
  --profile config/applicant_profile.json \
  --resume-dir resumes \
  --headed \
  --no-persist
```

If the result is correct, repeat without `--no-persist`:

```bash
python -u run_browser_application.py \
  --board-token <board_token> \
  --greenhouse-job-id <greenhouse_job_id> \
  --profile config/applicant_profile.json \
  --resume-dir resumes \
  --headed
```

## Outcomes

`NEEDS_ASSISTANCE`
- CAPTCHA/challenge detected, required human fields, fill failure,
  policy mismatch, missing resume resolution, or safety issue.

`READY_NO_SUBMIT`
- deterministic browser filling completed and no human blocker remains.
- the application is still **not submitted**.

## Local artifacts

Example:

```text
browser_runs/orchestrator/<board>_<job_id>/
  inspection.json
  fill.json
  handoff.json
  handoff.md
  orchestrator.json
```

These artifacts are redacted but should remain private/ignored.
