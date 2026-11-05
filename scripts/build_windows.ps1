$ErrorActionPreference = 'Stop'

# Build a one-file GUI app. It still reads/writes settings under the user's
# %APPDATA%\LTA_UPLOAD folder; it does not change any window layouts or UX.
$pyArgs = @(
    '--noconfirm',
    '--clean',
    '--onefile',
    '--windowed',
    '--name', 'LTA-UPLOAD',
    '--collect-all', 'librosa',
    '--collect-submodules', 'keyring.backends',
    '--collect-submodules', 'googleapiclient',
    '--collect-data', 'tzdata',
    '--collect-binaries', 'soundfile',
    'gui.py'
)
python -m PyInstaller @pyArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

New-Item -ItemType Directory -Force -Path 'release' | Out-Null
Copy-Item 'dist/LTA-UPLOAD.exe' 'release/LTA-UPLOAD.exe' -Force
Copy-Item '.build/ffmpeg.exe' 'release/ffmpeg.exe' -Force
Copy-Item '.build/ffprobe.exe' 'release/ffprobe.exe' -Force
Copy-Item '.build/FFMPEG_LICENSE.txt' 'release/FFMPEG_LICENSE.txt' -Force
Copy-Item 'THIRD_PARTY_NOTICES.txt' 'release/THIRD_PARTY_NOTICES.txt' -Force
Copy-Item 'RELEASE_START_HERE.txt' 'release/START_HERE.txt' -Force
Write-Host 'Portable LTA UPLOAD release folder prepared.'
