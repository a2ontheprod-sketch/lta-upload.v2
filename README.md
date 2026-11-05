# LTA // UPLOAD — GitHub Windows Build (v2)

**Start with [V2_SETUP_AND_CHANGES.md](V2_SETUP_AND_CHANGES.md).**

# LTA // UPLOAD

A local Windows beat-to-video creator and YouTube uploader for LISTENTOAARXN.
**Same app and same pink/white interface; GitHub now builds the Windows EXE.**

## Start here

1. Read **[GITHUB_SETUP_GUIDE.md](GITHUB_SETUP_GUIDE.md)**.
2. Push this extracted folder to a GitHub repository (preferably via GitHub Desktop).
3. In **Actions**, run **Build LTA UPLOAD for Windows**.
4. Download its `LTA-UPLOAD-Windows` artifact, extract everything, and run
   `LTA-UPLOAD.exe` with `ffmpeg.exe` and `ffprobe.exe` beside it.

The EXE is created by your own GitHub Actions run; it is **not** prebuilt in
this repository ZIP. Read **[GITHUB_TROUBLESHOOTING.md](GITHUB_TROUBLESHOOTING.md)**
if a step fails, or **[README_FIRST.md](README_FIRST.md)** for full app setup,
YouTube OAuth, BeatStars and optional Pexels details.

## What changed?

- **Added:** GitHub Actions workflow, PowerShell packaging scripts, portable
  third-party FFmpeg binaries in release artifact, detailed guides.
- **Tiny internal runtime change:** When running as an EXE only, the launcher
  looks for `ffmpeg.exe` and `ffprobe.exe` in the same folder as the EXE.
- **Not changed:** pink-and-white UI, audio analysis, static cover image
  rendering, SEO metadata, YouTube API integration/scheduling, BeatStars
  assisted mode, Pexels support and local app settings.

This is a Windows source project with a CI build recipe. The Windows/GitHub
build and OAuth cannot be validated without a real GitHub Actions run and your
Google credentials. Never upload credentials into a GitHub repository.
