# LTA // UPLOAD v2 — GitHub upgrade

## Install the update through GitHub (browser only)

1. Download and extract the v2 GitHub project ZIP.
2. Open your existing `LTA-UPLOAD` GitHub repository on the **Code** tab.
3. Upload the updated `gui.py`, `core.py`, and new `V2_SETUP_AND_CHANGES.md` to the repository root using **Add file → Upload files**. Keep the existing `.github/workflows/build-windows.yml`, scripts, and other files. GitHub may ask you to confirm overwriting existing files. If browser upload won't replace existing files, open each file, click Edit, and paste its replacement contents instead.
4. Commit the changes to `main`.
5. Open **Actions → Build LTA UPLOAD for Windows**, run the workflow, and download the newest successful `LTA-UPLOAD-Windows` artifact.
6. Extract the new artifact completely and run `LTA-UPLOAD.exe` (do not run the old EXE).

## What's changed

- Four-step wizard: Beats → Details & artwork → Publish settings → Review & upload.
- Selected beat now prominently labeled; table uses full-row selection.
- Artwork is centered with black padding in generated videos and thumbnails, not cropped.
- Improved heuristic BPM estimation from onset tempo and key estimation from harmonic audio. **Automatic detection remains an estimate and is not guaranteed accurate**; correct BPM and key manually in the table. Tempo can be detected at half or double its intended rate.
- Calendar widget explicitly assigned to scheduled date control.
- Short, low-volume click sound on app buttons and animated wizard transitions.
- Existing rendering/upload progress bar and activity log remain on screen.
- YouTube OAuth errors now explain the Google Cloud client JSON requirement.

## YouTube connection (required for direct YouTube upload)

1. In Google Cloud Console create a project, enable **YouTube Data API v3**, and configure OAuth consent.
2. Create an **OAuth client ID** of type **Desktop app** and download its JSON file.
3. If your app is in OAuth testing mode, add your Google account under test users.
4. In LTA // UPLOAD click **Settings** and browse for the downloaded desktop client JSON.
5. Click **Connect YouTube** and authorize in the browser. The app never asks for your Google password.
6. If the app is unverified or a newly created API project has upload restrictions, check Google API project verification/audit requirements. Uploads may be restricted to private.

## BeatStars (important limitation)

There is no confirmed official BeatStars public upload API in this project. The BeatStars option is **assisted**: use **Open BeatStars Studio**, log in there, upload the beat manually, copy metadata from the app, and paste the direct track URL into the beat's table row. The app does **not** request or store your BeatStars password and cannot claim automatic BeatStars publication.

If YouTube + BeatStars are both checked, the app renders locally first. It intentionally holds YouTube upload until you have a direct BeatStars track link, so the description won't contain a fake license link. After adding the URL, run again; the completed local render can be reused.

## First test

Use one WAV or MP3 and an image. On Publish Settings, **uncheck YouTube and BeatStars** to render locally without signing in. On the final Review step inspect title, description, and tags; click **Generate & Upload**. You should see the activity log and pink progress bar. The generated MP4 is saved in the output folder configured in Settings.

## If Generate & Upload appears to do nothing

Check for a pop-up error and the status line. Typical blockers: no beats, missing artwork, no output folder, or YouTube checked without a connected channel. To test rendering alone, uncheck YouTube first. Keep the app open while rendering. If the process fails, copy the exact error message.

## Technical note

This update was syntax-checked and the existing six core tests passed in a Linux test environment. The GUI and OAuth flows were not tested in a real Windows session; the new Windows build must be checked on your machine. The v2 code does not claim to fix Google API account/configuration problems automatically.
