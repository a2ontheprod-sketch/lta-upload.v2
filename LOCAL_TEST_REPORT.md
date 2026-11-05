# LTA // UPLOAD — local validation report

Validation performed on November 5, 2026, in a Linux development sandbox (not on a Windows desktop):

- Python static/syntax compilation: passed (`core.py`, `youtube_api.py`, `gui.py`).
- Metadata title, direct BeatStars URL validation, editable genres and keywords: passed.
- YouTube tag length cap: passed.
- Europe/London timezone conversion and rejected nonexistent DST time: passed.
- SQLite duplicate-upload journal transitions: passed.
- FFmpeg generated and probed a real H.264/AAC static-image MP4 from a locally generated WAV: passed.
- `pytest` suite: **6 tests passed**.

Not tested in this environment:

- Actual Windows/PySide6 desktop rendering and clicking through the UI.
- YouTube OAuth sign-in with your personal Google account.
- YouTube upload, thumbnail publishing, scheduling and Google quota behaviour with your account.
- Pexels API access with a real key.
- BeatStars publish operation. BeatStars is intentionally a manual-assisted workflow.

The project should be treated as an implementation that requires a first-run Windows acceptance test, rather than a verified production installer. Read `README_FIRST.md` to configure the services and test a private YouTube upload before going public.
