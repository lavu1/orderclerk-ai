# Final validation — 11 September 2026

- 9 focused automated tests passed locally.
- 4 actual local-model scenarios passed; see LIVE_MODEL_EVIDENCE.json and scripts/verify_live.py.
- Browser workflows checked against persisted state and captured in submission/media.
- Source and synthetic assets exclude credentials, databases, caches and virtual environments.
- Real model failures found during testing are documented alongside the guards added in response.
- Video is H.264/AAC, 1920 by 1080, under five minutes; representative frames and screenshot content were visually reviewed.
- Public source and video status: PUBLICATION.md. No event submission receipt exists yet.

Browser checks: written-number extraction, correct K155 total, CSV link, replay with unchanged stock, missing-quantity review and shortage review. Fixed a CSS rule that left the empty placeholder visible after completion. Database migration preserves prior orders and foreign-key integrity.
