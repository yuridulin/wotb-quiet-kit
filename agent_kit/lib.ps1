$ErrorActionPreference = "Stop"

function Fail([string]$Message) {
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Get-Sha256([string]$Path) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
        try {
            $hash = $sha.ComputeHash($stream)
        }
        finally {
            $stream.Dispose()
        }
        ([BitConverter]::ToString($hash) -replace "-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Test-GameRoot([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    Test-Path -LiteralPath (Join-Path $Path "Data\WwiseSound")
}

function Resolve-GamePath {
    param(
        [string]$Explicit,
        [string]$PackageRoot
    )

    $candidates = New-Object System.Collections.Generic.List[string]
    if ($Explicit) { $candidates.Add($Explicit) }
    if ($env:WOTB_GAME_PATH) { $candidates.Add($env:WOTB_GAME_PATH) }

    $gamePathFile = Join-Path $PackageRoot "gamepath.txt"
    if (Test-Path -LiteralPath $gamePathFile) {
        $candidates.Add((Get-Content -LiteralPath $gamePathFile -Raw).Trim())
    }

    $steamRoots = @(
        "${env:ProgramFiles(x86)}\Steam",
        "$env:ProgramFiles\Steam"
    )
    $steamKey = Get-ItemProperty -Path "HKCU:\Software\Valve\Steam" -Name SteamPath -ErrorAction SilentlyContinue
    if ($steamKey -and $steamKey.SteamPath) { $steamRoots += ($steamKey.SteamPath -replace '/', '\') }

    foreach ($steam in ($steamRoots | Where-Object { $_ } | Select-Object -Unique)) {
        $candidates.Add((Join-Path $steam "steamapps\common\World of Tanks Blitz"))
        $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
        if (Test-Path -LiteralPath $vdf) {
            $hits = Select-String -LiteralPath $vdf -Pattern '"path"\s+"([^"]+)"' -AllMatches
            foreach ($hit in $hits) {
                foreach ($match in $hit.Matches) {
                    $library = $match.Groups[1].Value -replace '\\\\', '\'
                    $candidates.Add((Join-Path $library "steamapps\common\World of Tanks Blitz"))
                }
            }
        }
    }

    $candidates.Add("D:\Program Files (x86)\Steam\steamapps\common\World of Tanks Blitz")
    $candidates.Add("C:\Program Files (x86)\Steam\steamapps\common\World of Tanks Blitz")
    $candidates.Add("C:\Program Files\Steam\steamapps\common\World of Tanks Blitz")
    $candidates.Add("C:\Games\World of Tanks Blitz")
    $candidates.Add("D:\Games\World of Tanks Blitz")

    foreach ($candidate in ($candidates | Where-Object { $_ } | Select-Object -Unique)) {
        if (Test-GameRoot $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Assert-GameStopped {
    $proc = Get-Process -Name "wotblitz" -ErrorAction SilentlyContinue
    if ($proc) {
        Fail "World of Tanks Blitz is running (wotblitz.exe). Close it and retry."
    }
}

function Test-PathInside {
    param([string]$Root, [string]$Child)
    $rootFull = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $childFull = [IO.Path]::GetFullPath($Child)
    $childFull.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)
}
