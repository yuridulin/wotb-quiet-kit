[CmdletBinding()]
param(
    [string]$GamePath = "",
    [string]$OverlayPath = "",
    [string]$BackupDir = "",
    [switch]$DryRun,
    [switch]$Force,
    [switch]$RemoveBackup
)

$ErrorActionPreference = "Stop"
$PackageRoot = $PSScriptRoot
. (Join-Path $PackageRoot "lib.ps1")

$gameRoot = Resolve-GamePath -Explicit $GamePath -PackageRoot $PackageRoot
if (-not $gameRoot) {
    Fail "Game not found. Pass -GamePath 'D:\path\World of Tanks Blitz' or create gamepath.txt."
}
$dataRoot = Join-Path $gameRoot "Data"
Assert-GameStopped

if (-not $BackupDir) {
    $backupRoot = Join-Path $gameRoot "_mod_backup\quiet_11.21"
    if (-not (Test-Path -LiteralPath $backupRoot)) {
        Fail "No quiet_11.21 backup found under $backupRoot"
    }
    $latest = Get-ChildItem -LiteralPath $backupRoot -Directory |
        Sort-Object Name -Descending |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "install.json") } |
        Select-Object -First 1
    if (-not $latest) { Fail "No install.json found under $backupRoot" }
    $BackupDir = $latest.FullName
}

$installFile = Join-Path $BackupDir "install.json"
if (-not (Test-Path -LiteralPath $installFile)) { Fail "install.json not found: $installFile" }
$install = Get-Content -LiteralPath $installFile -Raw -Encoding UTF8 | ConvertFrom-Json

$overlayRoot = if ($OverlayPath) {
    $OverlayPath
}
elseif ($install.overlayPath) {
    [string]$install.overlayPath
}
else {
    Join-Path $env:LOCALAPPDATA "wotblitz\packs"
}

function Get-RecordArea($Record) {
    $area = [string]$Record.area
    if ([string]::IsNullOrWhiteSpace($area)) { return "data" }
    return $area
}

function Get-EntryRoot([string]$Area) {
    if ($Area -eq "overlay") { return $overlayRoot }
    return $dataRoot
}

$records = @($install.files)

Write-Host "Game:    $gameRoot"
Write-Host "Overlay: $overlayRoot"
Write-Host "Backup:  $BackupDir"
Write-Host "Files:   $($records.Count)"

$problems = New-Object System.Collections.Generic.List[string]
foreach ($record in $records) {
    $area = Get-RecordArea $record
    if ($area -notin @("data", "overlay")) {
        $problems.Add("unknown area '$area': $($record.path)")
        continue
    }
    $root = Get-EntryRoot $area
    $target = Join-Path $root $record.path
    if (-not (Test-PathInside -Root $root -Child $target)) {
        $problems.Add("unsafe path: $($record.path)")
        continue
    }

    if ($record.existed) {
        if (-not (Test-Path -LiteralPath $record.backupPath)) {
            $problems.Add("backup missing: $($record.path)")
            continue
        }
        if ((Get-Sha256 $record.backupPath) -ne $record.backupSha256.ToLowerInvariant()) {
            $problems.Add("backup hash mismatch: $($record.path)")
            continue
        }
        if (-not (Test-Path -LiteralPath $target)) {
            $problems.Add("installed file missing: $($record.path)")
            continue
        }
        if ((Get-Sha256 $target) -ne $record.installedSha256.ToLowerInvariant() -and -not $Force) {
            $problems.Add("installed file changed since install: $($record.path)")
        }
    }
    else {
        if (Test-Path -LiteralPath $target) {
            if ((Get-Sha256 $target) -ne $record.installedSha256.ToLowerInvariant() -and -not $Force) {
                $problems.Add("added file changed since install: $($record.path)")
            }
        }
    }
}

if ($problems.Count -gt 0) {
    Write-Host ""
    Write-Host "Preflight failed ($($problems.Count) problem(s)):" -ForegroundColor Red
    $problems | Select-Object -First 15 | ForEach-Object { Write-Host "  - $_" }
    if ($problems.Count -gt 15) { Write-Host "  ..." }
    Write-Host ""
    Write-Host "Nothing was changed. Use -Force only if you accept overwriting current files."
    exit 2
}

if ($DryRun) {
    Write-Host ""
    Write-Host "DRY RUN: all checks passed. Nothing was written."
    exit 0
}

foreach ($record in $records) {
    $area = Get-RecordArea $record
    $root = Get-EntryRoot $area
    $target = Join-Path $root $record.path
    if ($record.existed) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $record.backupPath -Destination $target -Force
        if ((Get-Sha256 $target) -ne $record.backupSha256.ToLowerInvariant()) {
            throw "restore verification failed: $($record.path)"
        }
    }
    elseif (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Force
    }
}

Write-Host ""
Write-Host "Restored $($records.Count) file(s)." -ForegroundColor Green
if ($RemoveBackup) {
    Remove-Item -LiteralPath $BackupDir -Recurse -Force
    Write-Host "Removed backup: $BackupDir"
}
else {
    Write-Host "Backup kept: $BackupDir"
}
