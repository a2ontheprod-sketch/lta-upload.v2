$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# Obtain a Windows FFmpeg distribution to ship alongside the app.
# The app needs both ffmpeg.exe (render) and ffprobe.exe (audio duration).
$archive = Join-Path $env:RUNNER_TEMP 'lta_ffmpeg.zip'
$unpacked = Join-Path $env:RUNNER_TEMP 'lta_ffmpeg_unpacked'
$uri = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
Write-Host "Downloading FFmpeg distribution: $uri"
Invoke-WebRequest -Uri $uri -OutFile $archive -MaximumRedirection 5
$hashResponse = (Invoke-WebRequest -Uri ($uri + '.sha256') -MaximumRedirection 5).Content
$hashMatch = [regex]::Match([string]$hashResponse, '(?i)\b[0-9a-f]{64}\b')
if (!$hashMatch.Success) { throw 'Could not read the publisher SHA-256 checksum.' }
$expectedHash = $hashMatch.Value.ToUpperInvariant()
$actualHash = (Get-FileHash -Path $archive -Algorithm SHA256).Hash.ToUpperInvariant()
if ($actualHash -ne $expectedHash) { throw 'FFmpeg download SHA-256 verification failed.' }
Write-Host 'FFmpeg archive checksum verified against publisher manifest.'
Expand-Archive -Path $archive -DestinationPath $unpacked -Force

$ffmpeg = Get-ChildItem $unpacked -Recurse -File -Filter 'ffmpeg.exe' | Select-Object -First 1
$ffprobe = Get-ChildItem $unpacked -Recurse -File -Filter 'ffprobe.exe' | Select-Object -First 1
if (!$ffmpeg -or !$ffprobe) { throw 'The downloaded archive did not include both ffmpeg.exe and ffprobe.exe.' }
if ($ffmpeg.DirectoryName -ne $ffprobe.DirectoryName) { throw 'FFmpeg tools were not located in the same folder.' }

# Preserve the licence document distributed with the FFmpeg binary.
$licence = Get-ChildItem $unpacked -Recurse -File |
    Where-Object { $_.Name -match '^(LICENSE|COPYING)(\.[A-Za-z0-9_-]+)?$' } |
    Select-Object -First 1
# These Gyan static Windows builds are GPLv3; the repository also retains
# GPL-3.0 text so it can be included even if upstream changes its ZIP layout.
if (!$licence -and !(Test-Path 'third_party/GPL-3.0.txt')) {
    throw 'No FFmpeg licence document was available to package.'
}

$work = Join-Path (Get-Location) '.build'
New-Item -ItemType Directory -Path $work -Force | Out-Null
Copy-Item $ffmpeg.FullName (Join-Path $work 'ffmpeg.exe') -Force
Copy-Item $ffprobe.FullName (Join-Path $work 'ffprobe.exe') -Force
if ($licence) {
    Copy-Item $licence.FullName (Join-Path $work 'FFMPEG_LICENSE.txt') -Force
} else {
    Copy-Item 'third_party/GPL-3.0.txt' (Join-Path $work 'FFMPEG_LICENSE.txt') -Force
}

# Make the tools available to subsequent GitHub Actions steps, including pytest.
Add-Content -Path $env:GITHUB_PATH -Value $work
Write-Host 'Downloaded FFmpeg, ffprobe and their included licence.'
