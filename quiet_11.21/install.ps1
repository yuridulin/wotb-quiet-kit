[CmdletBinding()]
param(
    [string]$GamePath = "",
    [string]$OverlayPath = "",
    [switch]$DryRun,
    [switch]$Force,
    [switch]$SkipSound,
    [switch]$SkipUI,
    [switch]$SkipReticle,
    [switch]$SkipOverlay
)

$ErrorActionPreference = "Stop"
$PackageRoot = $PSScriptRoot
. (Join-Path $PackageRoot "lib.ps1")

if ($SkipSound -and $SkipUI -and $SkipReticle) {
    Fail "All -Skip switches were supplied; nothing to install."
}

$manifestPath = Join-Path $PackageRoot "manifest.json"
$payloadRoot = Join-Path $PackageRoot "payload"
if (-not (Test-Path -LiteralPath $manifestPath)) { Fail "manifest.json not found." }
if (-not (Test-Path -LiteralPath $payloadRoot)) { Fail "payload directory not found." }

$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$gameRoot = Resolve-GamePath -Explicit $GamePath -PackageRoot $PackageRoot
if (-not $gameRoot) {
    Fail "Game not found. Pass -GamePath 'D:\path\World of Tanks Blitz' or create gamepath.txt."
}
$dataRoot = Join-Path $gameRoot "Data"
$overlayRoot = if ($OverlayPath) { $OverlayPath } else { Join-Path $env:LOCALAPPDATA "wotblitz\packs" }
Assert-GameStopped

function Get-EntryArea($Entry) {
    $area = [string]$Entry.area
    if ([string]::IsNullOrWhiteSpace($area)) { return "data" }
    return $area
}

function Get-EntryRoot([string]$Area) {
    if ($Area -eq "overlay") { return $overlayRoot }
    return $dataRoot
}

function Get-PayloadPath($Entry) {
    $area = Get-EntryArea $Entry
    $prefix = if ($area -eq "overlay") { "Overlay" } else { "Data" }
    return (Join-Path $payloadRoot (Join-Path $prefix $Entry.path))
}

function Get-BackupPath($Entry, [string]$BackupDir) {
    $area = Get-EntryArea $Entry
    $prefix = if ($area -eq "overlay") { "Overlay" } else { "Data" }
    return (Join-Path $BackupDir (Join-Path $prefix $Entry.path))
}

$entries = @($manifest.files)
if ($SkipSound) { $entries = @($entries | Where-Object { $_.category -ne "sound" }) }
if ($SkipUI) { $entries = @($entries | Where-Object { $_.category -ne "ui" }) }
if ($SkipReticle) { $entries = @($entries | Where-Object { $_.category -ne "reticle" }) }
if ($SkipOverlay) { $entries = @($entries | Where-Object { (Get-EntryArea $_) -ne "overlay" }) }
if ($entries.Count -eq 0) { Fail "No files selected." }

$uiCount = @($entries | Where-Object { $_.category -eq "ui" }).Count
$soundCount = @($entries | Where-Object { $_.category -eq "sound" }).Count
$reticleCount = @($entries | Where-Object { $_.category -eq "reticle" }).Count
$overlayCount = @($entries | Where-Object { (Get-EntryArea $_) -eq "overlay" }).Count

Write-Host "Game:    $gameRoot"
Write-Host "Overlay: $overlayRoot"
Write-Host "Package: $($manifest.name) for $($manifest.gameVersion)"
Write-Host "Files:   $($entries.Count) ($uiCount UI, $soundCount sound, $reticleCount reticle, $overlayCount overlay)"

$problems = New-Object System.Collections.Generic.List[string]
$alreadyInstalled = 0
$blockedExtensions = @(".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".js")

foreach ($entry in $entries) {
    $area = Get-EntryArea $entry
    if ($area -notin @("data", "overlay")) {
        $problems.Add("unknown area '$area': $($entry.path)")
        continue
    }
    if ($entry.category -notin @("ui", "sound", "reticle")) {
        $problems.Add("unknown category '$($entry.category)': $($entry.path)")
        continue
    }
    $ext = [IO.Path]::GetExtension([string]$entry.path).ToLowerInvariant()
    if ($ext -in $blockedExtensions) {
        $problems.Add("refusing executable payload: $($entry.path)")
        continue
    }

    $root = Get-EntryRoot $area
    $target = Join-Path $root $entry.path
    if (-not (Test-PathInside -Root $root -Child $target)) {
        $problems.Add("unsafe path: $($entry.path)")
        continue
    }
    $source = Get-PayloadPath $entry
    if (-not (Test-Path -LiteralPath $source)) {
        $problems.Add("payload missing: $($entry.path)")
        continue
    }
    if ((Get-Sha256 $source) -ne $entry.sha256.ToLowerInvariant()) {
        $problems.Add("payload hash mismatch: $($entry.path)")
        continue
    }

    if ($entry.originalExisted) {
        if (-not (Test-Path -LiteralPath $target)) {
            $problems.Add("game file missing: $($entry.path)")
            continue
        }
        $hash = Get-Sha256 $target
        if ($hash -eq $entry.sha256.ToLowerInvariant()) {
            $alreadyInstalled++
            continue
        }
        if ($hash -ne $entry.originalSha256.ToLowerInvariant() -and -not $Force) {
            $problems.Add("game file differs from 11.21.0 baseline: $($entry.path)")
        }
    }
    else {
        if (Test-Path -LiteralPath $target) {
            $hash = Get-Sha256 $target
            if ($hash -eq $entry.sha256.ToLowerInvariant()) {
                $alreadyInstalled++
                continue
            }
            if (-not $Force) {
                $problems.Add("file already exists with different content: $($entry.path)")
            }
        }
    }
}

if ($alreadyInstalled -gt 0) {
    $problems.Add("$alreadyInstalled file(s) already match this package; run uninstall.ps1 first.")
}

if ($problems.Count -gt 0) {
    Write-Host ""
    Write-Host "Preflight failed ($($problems.Count) problem(s)):" -ForegroundColor Red
    $problems | Select-Object -First 15 | ForEach-Object { Write-Host "  - $_" }
    if ($problems.Count -gt 15) { Write-Host "  ..." }
    Write-Host ""
    Write-Host "Nothing was changed. Use -Force only for a deliberate overwrite."
    exit 2
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $gameRoot "_mod_backup\quiet_11.21"
$backupDir = Join-Path $backupRoot $stamp

if ($DryRun) {
    Write-Host ""
    Write-Host "DRY RUN: all checks passed. Nothing was written."
    Write-Host "Backup would be: $backupDir"
    exit 0
}

New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$records = New-Object System.Collections.Generic.List[object]
$installed = New-Object System.Collections.Generic.List[object]

try {
    foreach ($entry in $entries) {
        $area = Get-EntryArea $entry
        $root = Get-EntryRoot $area
        $target = Join-Path $root $entry.path
        $source = Get-PayloadPath $entry
        $existed = Test-Path -LiteralPath $target
        $backupFile = $null
        $backupHash = $null

        if ($existed) {
            $backupFile = Get-BackupPath $entry $backupDir
            New-Item -ItemType Directory -Path (Split-Path -Parent $backupFile) -Force | Out-Null
            Copy-Item -LiteralPath $target -Destination $backupFile -Force
            $backupHash = Get-Sha256 $backupFile
            if ($backupHash -ne (Get-Sha256 $target)) {
                throw "backup verification failed: $($entry.path)"
            }
        }

        $record = [pscustomobject]@{
            area = $area
            path = $entry.path
            category = $entry.category
            existed = $existed
            backupPath = $backupFile
            backupSha256 = $backupHash
            installedSha256 = $entry.sha256
        }
        $records.Add($record)
        $installed.Add($record)

        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Force
        if ((Get-Sha256 $target) -ne $entry.sha256.ToLowerInvariant()) {
            throw "installed file hash mismatch: $($entry.path)"
        }
    }

    $installRecord = @{
        package = $manifest.name
        gameVersion = $manifest.gameVersion
        installedAt = (Get-Date).ToString("o")
        gamePath = $gameRoot
        overlayPath = $overlayRoot
        backupDir = $backupDir
        files = $records.ToArray()
    }
    $json = $installRecord | ConvertTo-Json -Depth 6
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Join-Path $backupDir "install.json"), $json, $utf8NoBom)
}
catch {
    Write-Host ""
    Write-Host "Install failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Rolling back changed files..." -ForegroundColor Yellow
    for ($i = $installed.Count - 1; $i -ge 0; $i--) {
        $record = $installed[$i]
        $root = Get-EntryRoot $record.area
        $target = Join-Path $root $record.path
        try {
            if ($record.existed) {
                New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
                Copy-Item -LiteralPath $record.backupPath -Destination $target -Force
            }
            elseif (Test-Path -LiteralPath $target) {
                Remove-Item -LiteralPath $target -Force
            }
        }
        catch {
            Write-Host "  rollback failed: $($record.path): $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    throw
}

Write-Host ""
Write-Host "Installed $($records.Count) file(s)." -ForegroundColor Green
Write-Host "Backup: $backupDir"
Write-Host "Uninstall: powershell -NoProfile -ExecutionPolicy Bypass -File `"$PackageRoot\uninstall.ps1`""
