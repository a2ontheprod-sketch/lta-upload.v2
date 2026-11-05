# GitHub Windows .EXE build now included

**Recommended new installation method:** Upload this repository to GitHub,
run its **Build LTA UPLOAD for Windows** Action, download the
`LTA-UPLOAD-Windows` artifact and double-click `LTA-UPLOAD.exe` after
extracting its FFmpeg files alongside it. **See `GITHUB_SETUP_GUIDE.md` for
the complete numbered guide.** No separate Python/FFmpeg installation is
required for the GitHub-built artifact. The instructions below still describe
the original source-code/`.bat` fallback method and the unchanged app features.

---

# LTA // UPLOAD

Local Windows beat-to-video utility for LISTENTOAARXN. This is a **source-code project you can run**, not a precompiled .exe. The interface is PySide6, local processing uses FFmpeg/librosa, and uploads use the official YouTube Data API.

> **Integration status:** Real MP4 rendering is implemented and testable without any login. The YouTube integration calls the real Google APIs but **has not been authenticated or live-upload tested with your channel** because it requires your Google Cloud desktop OAuth file and account permission. BeatStars is **assisted upload**, not automatic publishing: BeatStars has not announced a supported public upload API. Never mistake a local video for a completed YouTube/BeatStars upload.

## Step-by-step Windows installation

### 1. Unzip the project

Extract `LTA_UPLOAD.zip` into a folder such as `C:\LTA_UPLOAD`. Do not run the `.bat` from inside the ZIP preview.

### 2. Install Python 3.11 or 3.12

Install Python 3.11 or Python 3.12 for Windows from https://www.python.org/downloads/windows/ . Check **Add python.exe to PATH** when offered. This app has been authored for 3.11/3.12; other versions may work but have not been validated.

### 3. Install FFmpeg

FFmpeg does the real MP4 rendering; the app will not render without it.

- Option A: Open PowerShell / Windows Terminal and run `winget install Gyan.FFmpeg`. Close/reopen your terminal after install.
- Option B: Download a Windows build from https://ffmpeg.org/download.html , extract it, and add the folder containing `ffmpeg.exe` and `ffprobe.exe` to the **user PATH** in Windows Environment Variables.
- Verify in a new Command Prompt by running `ffmpeg -version` and `ffprobe -version`. Both should print a version.

### 4. Double-click `INSTALL_AND_START.bat`

On first run it creates a local `.venv` and installs dependencies from `requirements.txt`. Internet is required for the initial install. Afterwards it launches the pink-and-white app. This launcher is **not an `.exe` installer**. Leave the original folder intact.

### 5. Add a beat and test local rendering first

- Drag an MP3 or WAV onto the drop area, or click to browse. Multiple beats can be added at once.
- In the table, double-click the beat name, BPM, key or BeatStars track URL to edit them. BPM/key are **estimates**; manual corrections are encouraged.
- Type two artist names. For example: `Fimiguerrero` and `Lancey Foux`.
- Choose an artwork image, use the included generated pink abstract default, or click **Find on Pexels** (API key required; see below).
- Uncheck **YouTube** for the first test. Leave **BeatStars assisted** unchecked.
- Click **Generate & Upload**. With no publishing service selected, it **renders locally only**.
- MP4s save under `Videos\LTA Upload` by default, or in the folder set under **Settings**. The rendered image stays completely static and only the beat plays.
- Check the `UPLOAD ACTIVITY` panel for the output path. If rendering fails, verify FFmpeg is accessible in PATH and that the MP3/WAV is valid.

## Connect your real YouTube channel (one-time Google Cloud setup)

1. Open https://console.cloud.google.com/ and create/select your own Google Cloud project.
2. Go to **APIs & Services > Library** and enable **YouTube Data API v3**.
3. In **Google Auth Platform / OAuth consent screen**, configure the app and required consent details. If in Testing with External user type, add your Google Account to the test users list. Follow any verification/security prompts Google requires.
4. Go to **Clients / Credentials > Create client > OAuth client ID** and choose **Desktop app** (not Web application). Download the **client JSON**. Do not share the file publicly.
5. In LTA // UPLOAD click **Settings**, browse to that JSON under **Google OAuth desktop JSON**, and save.
6. Click **Connect YouTube**. Your normal browser opens Google's OAuth permission flow. Sign in with the Google Account that manages the intended YouTube channel and approve the requested upload/read scopes. **Do not enter your Google password into LTA // UPLOAD.**
7. The app reports the connected channel name. You can now tick YouTube, choose Public/Private/Unlisted/Scheduled, and upload real videos.
8. OAuth tokens are kept through the system keyring (on Windows, Windows Credential Manager) and reused on launch. Use **Disconnect** to remove the local credentials. Connection can be re-established when needed.
9. On first test, choose **Private**, render/upload one short beat and confirm it appears in your YouTube Studio before running a batch.

**Native scheduling:** Choose **Scheduled**, select the **Europe/London** wall-clock date and time, then click **Generate & Upload**. The app sends a UTC `publishAt` value on a private upload. Once confirmed, Google's servers handle future publication, even when your PC is off. Time must be in the future; daylight-saving nonexistent times are rejected.

**Important YouTube limits:** Google enforces title, description, tags, upload, quotas and thumbnail privileges. A quota or permissions error is real, not simulated. If the request is interrupted **after upload began**, check YouTube Studio before retrying: the app marks the upload as uncertain and prevents an automatic duplicate. The tracking database is in `%APPDATA%\LTA_UPLOAD\uploads.sqlite3`; do not delete or reset it unless you have manually verified the channel state. Current Google API docs: https://developers.google.com/youtube/data/reference/rest/v3/videos/insert and https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set .

## BeatStars: assisted upload workflow

BeatStars publicly stated in September 2025 that it had no immediate plans to release a public API for upload/content management. Source: https://requests.beatstars.com/ideas/PROD-I-452 . Therefore LTA // UPLOAD **does not claim to automatically upload to BeatStars**. No account credentials are collected.

1. Tick **BeatStars assisted**.
2. Click **Copy selected beat details for BeatStars** to copy the BPM, key, tags and optional licence note; then click **Open BeatStars Studio ↗** and sign in on BeatStars' website.
3. Upload the original beat and artwork there, paste the copied information where useful, set your desired actual licence/splits/prices, and publish it. LTA does not edit your licence agreements.
4. Copy the **direct URL for the individual published beat** (for example, a `/beat/track-title` link, not a BeatStars profile or homepage).
5. Paste it into the **BeatStars track URL** cell of that beat's row in the app.
6. When YouTube is ticked too, LTA generates the description with the correct direct link and uploads the YouTube video. If BeatStars is ticked but its direct link is missing, the app **renders locally and intentionally skips YouTube** to avoid publishing a dead purchase link. Paste the link and press Generate & Upload again to continue; existing rendered MP4s are reused.

If you want a stronger BeatStars integration later, the safest direction is a separate, opt-in human-supervised browser-assisted workflow, subject to BeatStars' terms; this project does not deploy an unverified browser bot.

## Optional Pexels artwork search

1. Create an API key at https://www.pexels.com/api/ .
2. Add it to **Settings > Pexels API key**. It is stored in the OS credential store, not settings.json.
3. Click **Find on Pexels** and search a visual mood, e.g. `dreamy city at night`, `vintage internet`, or `abstract pink`.
4. Select an image from the results. The downloaded image is saved locally and the photographer/Pexels source are appended to the generated YouTube description. The dialog also links back to Pexels.
5. Read Pexels' API and photo licence terms. Do not assume third-party trademarks, identifiable people or pictured artwork have a blanket promotional clearance. Pexels API docs: https://www.pexels.com/api/documentation/ .

## Metadata and batch use

- Add any number of MP3/WAV files. Every row has an editable beat name, BPM, key and BeatStars URL. Artist combination, artwork, mood, genre, resolution and publish mode apply to the whole batch.
- The selected row has an editable title, description and comma-separated YouTube tag input. Clicking a pink tag chip removes it. **Only manually edited fields are locked**; automatically generated fields update when artists, mood or BPM change.
- The app uses conservative templates and an editable local keyword dictionary at `%APPDATA%\LTA_UPLOAD\artists.json`. It does **not** fabricate audio observations or claim to have performed AI research. For unknown artists, tags use their names and generic query variations rather than made-up scene associations.
- The default metadata adds Instagram `@listentoaarxn`. Enter your real public contact email in Settings; the app does not guess one.
- If you want to publish a beat directly without a BeatStars purchase link, leave the BeatStars URL blank and **untick BeatStars assisted**. The BUY / LICENSE section is then omitted rather than pointing to a nonexistent individual beat.
- Audio preview uses Qt's system codecs; if playback is silent on Windows, FFmpeg rendering can still work independently.

## Where data is stored

- Settings, editable artist metadata, generated/default artwork, and upload journal: `%APPDATA%\LTA_UPLOAD\`
- Saved OAuth token and Pexels API key: system credential store via Python `keyring` (not project files).
- Rendered videos and jpg thumbnails: default `Videos\LTA Upload`, adjustable in Settings.
- Uploaded videos themselves: your connected YouTube channel.
- No secret values are included in the distributed ZIP.

## Technical notes and limitations

- Local rendering uses H.264 video and AAC at 320 kb/s, static full-screen artwork, no filters/compressors/mastering. MP3 and WAV cannot be reproduced bit-for-bit in AAC; expected audio changes are from encoding only.
- Default video is 1920×1080 at 24 fps, with 1280×720 and 2560×1440 options. Large batches take processing and network time even though filling out fields is fast.
- Key and BPM estimation uses librosa and correlation of mean chroma against Krumhansl key templates. Half-time/double-time BPMs and mixed harmonic material can be mistaken; correct manually.
- YouTube resuming uses a single live resumable session with backoff for temporary failures. If the process crashes after a request has started, it **blocks blind replay** until you check YouTube Studio, rather than risk duplicate uploads. This is deliberate.
- For critical use, keep original audio and artwork backed up. Test with private uploads before publishing multiple beats.
- File provided for this request cut off mid-BeatStars section after “Apply my saved licence”; later unspecified requirements could not be included.
- Code has local automated tests in `tests/`. Run them with `".venv\Scripts\python.exe" -m pip install pytest`, then `".venv\Scripts\python.exe" -m pytest tests -v` from the project folder.
