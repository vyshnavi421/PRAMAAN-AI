# Frontend fix notes (static review pass)

Verified: all 33 frontend API calls map to real backend routes; all JS files pass `node --check`.
NOT verified: backend tests / live server (no network in the review sandbox to install FastAPI). Run `python -m pytest backend/tests` locally.

## Fixed
1. **XSS**: uploaded filenames, institution names, error messages, rule text were injected into `innerHTML` unescaped. Added `static/js/util.js` (`esc`) and applied it across all views; toasts now use `textContent`.
2. **Auth header bug** (`api.js`): `{headers, ...options}` let `options.headers` overwrite the merged headers (dropping `Authorization`). Order fixed.
3. **Fake audit target** (`app.js`): decision modal fell back to a hardcoded finding id `f1a2b3c4-1111` and user `usr-officer-01`. Now requires a selected finding, uses the signed-in user, enforces the 10-char dismissal justification client-side, and disables the button while submitting.
4. **Fabricated evidence fallbacks** (`evidenceStudio.js`): removed made-up values (`2024-01-14`, `Cutoff 2026-06-30`, `APP-2026-EOA-108`, "EXPIRED" label for any deficiency). Missing data is now shown honestly, per AGENTS.md.
5. Health badge no longer hardcodes "Port 8000".
