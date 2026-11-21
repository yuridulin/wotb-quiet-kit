[CmdletBinding()]
param(
    [string]$GamePath = "",
    [string]$OverlayPath = "",
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PackageRoot "lib.ps1")

$gameRoot = Resolve-GamePath -Explicit $GamePath -PackageRoot $PackageRoot
if (-not $gameRoot) {
    Fail "Game not found. Pass -GamePath 'D:\path\World of Tanks Blitz'."
}
Assert-GameStopped

$profilePath = Join-Path $PackageRoot "vendor\sound_mod\profile.json"
if (-not (Test-Path -LiteralPath $profilePath)) {
    Fail "vendor/sound_mod/profile.json not found."
}
$profile = Get-Content -LiteralPath $profilePath -Raw -Encoding UTF8 | ConvertFrom-Json
$soundVersion = [string]$profile.gameVersion
if ([string]::IsNullOrWhiteSpace($soundVersion)) {
    Fail "profile.json has no gameVersion."
}

$reticleProfilePath = Join-Path $PackageRoot "vendor\reticle\profile.json"
if (-not (Test-Path -LiteralPath $reticleProfilePath)) {
    Fail "vendor/reticle/profile.json not found."
}
$reticleProfile = Get-Content -LiteralPath $reticleProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
$reticleVersion = [string]$reticleProfile.gameVersion
if ([string]::IsNullOrWhiteSpace($reticleVersion)) {
    Fail "reticle profile.json has no gameVersion."
}

$gameVersion = $null
$logDir = Join-Path $env:LOCALAPPDATA "wotblitz\DAVAProject"
if (Test-Path -LiteralPath $logDir) {
    $log = Get-ChildItem -LiteralPath $logDir -Filter "blitz-logs_*.txt" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($log) {
        $hit = Select-String -LiteralPath $log.FullName -Pattern 'currentBuildInfoStr\s*=\s*([0-9]+\.[0-9]+\.[0-9]+)' |
            Select-Object -First 1
        if ($hit) { $gameVersion = $hit.Matches[0].Groups[1].Value }
    }
}

if (-not $gameVersion) {
    Fail "Cannot determine game version. Launch the patched game once, then retry."
}
Write-Host "Game:      $gameVersion"
Write-Host "Sound mod: $soundVersion"
Write-Host "Reticle:   $reticleVersion"
if ($gameVersion -ne $soundVersion) {
    Fail "Sound mod version mismatch. Download a sound mod for $gameVersion, replace vendor/sound_mod, then retry."
}
if ($gameVersion -ne $reticleVersion) {
    Fail "Reticle mod version mismatch. Replace vendor/reticle for $gameVersion, then retry."
}

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { Fail "python not found in PATH." }

$buildArgs = @((Join-Path $PSScriptRoot "build_payload.py"), "--game", $gameRoot)
if ($OverlayPath) { $buildArgs += @("--overlay", $OverlayPath) }
& $python @buildArgs
if ($LASTEXITCODE -ne 0) { Fail "build_payload.py failed." }

$installArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $PackageRoot "install.ps1"),
    "-GamePath", $gameRoot
)
if ($OverlayPath) { $installArgs += @("-OverlayPath", $OverlayPath) }
if ($DryRun) { $installArgs += "-DryRun" }
if ($Force) { $installArgs += "-Force" }

& powershell.exe @installArgs
exit $LASTEXITCODE
