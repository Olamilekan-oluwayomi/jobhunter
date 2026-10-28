# Interactive design preview

Run the frontend with `npm run dev`, then visit `/preview`. The live app has a
"Try the new design" link. The preview requires no backend or database.

## What to try

1. Open a role and read the skill-fit explanation and location restriction.
2. Save or unsave roles, then open Saved jobs.
3. Search by role, company or skill; filter by employment type and location.
4. Record a sample application from the detail panel. Open Applications,
   change its status, add notes, and switch between board and list views.
5. Change your role, skills, experience or location in My preferences.
6. Switch light/dark themes and inspect at phone width.

All jobs and the initial profile are fictional and visibly labelled. Actions
write only to `jobhunter-design-preview-v1` in browser local storage. No scraping,
notifications, uploads or applications are triggered. Preview state is separate
from the existing app's API and saved jobs. Clearing this storage key resets it.

## Design choices

Warm neutral surfaces, forest-green actions, readable role cards and persistent
navigation. Desktop job details use a native modal drawer, with Escape dismissal
and focus restoration. Mobile uses bottom navigation and a full-height detail
view. Search and filters are represented in the URL for back/forward navigation.

## Verification and limits

Frontend lint, production build and six simulated-DOM journey tests pass. Run
`npm test` in `frontend/` to exercise search, filters, saves, application status,
notes, dialog cancellation/focus restoration, profile persistence and themes. Browser
automation was unavailable in the implementation session; visual appearance,
mobile overflow, focus behavior and interactions need a real browser pass.
This is the prototype milestone, not a production multi-user release.

Next: review the visual direction, then connect these journeys to authenticated,
per-user API data. The preview's illustrative scoring is not the production
matcher and must not be substituted for it.
