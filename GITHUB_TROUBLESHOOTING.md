# LTA // UPLOAD — GitHub build and Windows troubleshooting

## I cannot see the workflow in Actions

Open the repository's **Code** tab. Verify that
`.github/workflows/build-windows.yml` exists at the repository root. If you
uploaded a ZIP as a single file, or put everything inside an extra folder,
GitHub cannot find the workflow. Upload the extracted contents instead.
The repository owner may also need to enable Actions in repository settings.

## My GitHub Actions build failed (red cross)

Click **Actions > failed run > build-windows**, expand the first red step, and
read the error. Typical reasons:

- `Install app and packaging dependencies`: Python package download/network,
  pinned wheel availability, or dependency compatibility failure.
- `Download FFmpeg`: the Gyan download is inaccessible, the archive has changed,
  or its checksum verification fails. The build refuses to publish
  an unverifiable FFmpeg download. Retry later or review that source distribution.
- `Run existing tests`: read the failing assertion/error; it runs a real MP4
  render on the Windows runner and checks the result using FFprobe.
- `Package unchanged app as a Windows EXE`: PyInstaller or optional dependency
  collection failure. Scroll to the first actual error, not just the last line.
- `Upload Windows download`: release files missing or repository Actions
  permissions/storage limits.

A green check proves tests and packaging steps completed. It **does not prove**
that Google OAuth, Windows UI clicking, audio playback on your machine or a
live YouTube upload succeeds; you still need to test those yourself.

## I downloaded a ZIP but I cannot find an EXE

There are two downloads: the **source project ZIP** and the **GitHub Actions
artifact ZIP**. Only the Actions artifact named `LTA-UPLOAD-Windows` contains
`LTA-UPLOAD.exe`. You must first upload the source project and run Actions.

## Windows says FFmpeg / FFprobe is missing

Put **LTA-UPLOAD.exe, ffmpeg.exe and ffprobe.exe in the same folder**. Don't
run from the ZIP preview. The GitHub EXE version automatically adds its own
folder to the PATH before importing the app. The original `.bat` source method
still requires FFmpeg installed separately.

## Windows Defender or SmartScreen says the EXE is unrecognised

This is an unsigned new application built in your GitHub repo. Don't disable
antivirus or security protections. Verify the GitHub run and files, scan them,
and only proceed if you trust the source and build. Signing can be added later.

## The app takes a while to open / downloaded EXE is large

PyInstaller `--onefile` extracts bundled Python and dependencies into a temp
folder on startup. The first launch may be slower than a normal lightweight
Windows app, especially because local audio analysis uses librosa.

## YouTube will not connect / auth consent error

Use an OAuth **Desktop app** JSON from your own Google Cloud project; ensure
YouTube Data API v3 is enabled, OAuth consent settings and any required test
users are configured. Keep the JSON on your PC, not in GitHub. Check Google
Cloud API restrictions, quotas and account/channel selection.

## Uploaded YouTube video not visible / restricted

The YouTube Data API can limit uploads from unverified API projects. Test a
Private upload first and inspect **YouTube Studio**. Do not re-upload blindly
when a previous upload might have succeeded; local duplicate protection may
mark ambiguous uploads for manual reconciliation.

## BeatStars isn't fully automatic

The existing app provides **assisted BeatStars publishing**, not an official
BeatStars upload integration. This is the same behaviour as the previous ZIP;
GitHub only changes packaging, not the external service's capabilities.

## My settings disappear after an update

Look in `%APPDATA%\LTA_UPLOAD` for `settings.json`, `artists.json`, artwork
and `uploads.sqlite3`. OAuth tokens are saved in Windows Credential Manager.
Do not delete the old AppData folder when updating the EXE. Back up personal
work before changing or removing an installation.
