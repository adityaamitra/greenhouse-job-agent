# Dashboard Assistance Handoff V1

This milestone upgrades the existing **Action Required → Needs Assistance**
section to display structured Browser Assistance Handoff V1 data.

## What changed

`src/App.jsx`
- queries unresolved `assistance_requests` with `source = 'BROWSER'`
- merges the latest browser request into its application row
- preserves the existing eligibility-assistance UI
- displays Browser V1 / CAPTCHA / ready / need-review badges
- displays the selected resume basename
- provides an expandable application handoff
- lists deterministic fields without exposing applicant profile values
- shows approved work-authorization/sponsorship policy answers only
- lists required and optional human-review questions
- surfaces a route-mismatch badge for historical test rows that were
  persisted before the V1.1 AGENT_APPLY-only route guard

`src/index.css`
- adds the Browser Assistance Handoff card and responsive styling

`src/lib/supabase.js`
- unchanged; included only so this bundle mirrors the relevant current
  dashboard source structure

## Database prerequisites

This UI expects the already-applied Browser Handoff migration fields on
`assistance_requests`:

- `source`
- `handoff`
- `handoff_version`
- `updated_at`

Existing RLS stays in place.

## Install

From the dashboard project root, replace:

```bash
cp <bundle>/src/App.jsx src/App.jsx
cp <bundle>/src/index.css src/index.css
```

`src/lib/supabase.js` does not need to be replaced if your current file is
unchanged.

## Local checks

```bash
python -u test_dashboard_assistance_handoff.py
npm run build
```

Expected static regression:

```text
Passed: 12/12
Failed: 0/12
```

## Expected Robinhood test-row UI

The existing historical Robinhood Browser V1 handoff should show:

- CAPTCHA
- 11 ready
- 10 need review
- `Software_Engineer.pdf`
- expandable deterministic and human-review sections
- Route mismatch, because that test row's latest matcher route is
  MANUAL_PRIORITY; V1.1 now prevents new non-AGENT_APPLY browser handoffs

Profile values must never be rendered from `display_answer`. Only
approved work-authorization/sponsorship policy keys may show Yes/No.
