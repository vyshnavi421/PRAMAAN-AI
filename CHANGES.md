# Changes in this revision
Fixed: missing `rapidfuzz` dependency; tenant-isolation gaps (review reports, validation runs, verification attempts);
server now reviews its own stored dossier (client copy ignored); AuditService tamper crash; fake "10/10" coverage in UI;
"ALL CLEAR" badge on unreviewed apps; sample certificate shown for empty dossiers; stale tests.
Added: disk persistence (PRAMAAN_DATA_DIR), POST /applications + UI dialog, printable scrutiny report,
draft deficiency letter (reviewer only), 14 regression tests (backend/tests/test_hardening_and_exports.py), run.sh.
Test status: full suite passed (0 skipped, 0 xfail) before the final small UI edit; UI smoke-tested in headless Chromium.
Also fixed in follow-up: README/AGENTS refreshed, fake fallback hashes removed from Evidence Studio, report + letter buttons and empty-dossier state verified in headless Chromium.
Not done: authenticated-login redesign, Postgres.
