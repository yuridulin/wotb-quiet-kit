# quiet_11.21 — local build implementation

> The shareable artifact is [`../INSTRUCTION.md`](../INSTRUCTION.md). This file
> documents the local implementation only; the recipient does not need it.

Goal: install three cosmetic parts on a local **World of Tanks Blitz 11.21.0**
(PC, Steam/Wargaming) without transferring the large mod archives.

**Distribution rule: this kit ships no mod archives and no payload.** All large
files are downloaded from the URLs below. Python + `lz4` is only the local build
tool used to repack DVPL; it is not a mod asset. Do not ask for or transfer a
prebuilt payload.

## Latest version first

Before downloading or building, check the latest release:

<https://github.com/yuridulin/wotb-quiet-kit/releases/latest>

Use the newest `quiet_11.21_agent.zip`. If the latest release is newer than this
kit, follow that release's `AGENT.md`; this source tree is pinned to 11.21.0.

## What is acquired where

| Part | Source | Expected SHA-256 |
|---|---|---|
| Sound: Gun Sounds from World of Tanks (DeltBlitz) | <https://blitz-mods.com/mod/gun-sounds/gun-sounds-from-world-of-tanks-301> → PC (WG) | `39189653a0f4ebefecc07ae49db2b1529f2344d0331b13b613d718e5df426290` |
| Reticle: WoT-style crosshair customization (DorTep, WG) | <https://forblitz.ru/storage/mods/21720/custom-aim-wot_pc_wg.zip> | `7fedda850033cb7de4ece784fefe76dfb31479a0b15b4cb10839e76ee9354047` |
| Lobby UI patch (16 YAML) | local `ui_src/Data` in this kit — custom edits, not downloadable | — |

The sound page uses a token interstitial. `bootstrap.py` handles it. If the site
blocks the agent, download the PC-WG zip manually and pass `--sound-zip <file>`.

## Paths

- Game root: auto-detect, or pass `--game "D:\...\World of Tanks Blitz"`.
- Game Data: `<Game>\Data`.
- Micropatch overlay: `%LOCALAPPDATA%\wotblitz\packs`.
- Kit downloads: `downloads/`.
- Generated payload: `payload/Data` + `payload/Overlay`.
- Generated manifest: `manifest.json`.
- Backup after install: `<Game>\_mod_backup\quiet_11.21\<timestamp>`.

## Prerequisites

- Windows 10/11, PowerShell 5.1+.
- Python 3.10+ and `py` launcher.
- `pip install -r requirements.txt` (only `lz4`).
- Game **closed** (`wotblitz.exe` not running).
- Game launched at least once, so `%LOCALAPPDATA%\wotblitz\DAVAProject\blitz-logs_*.txt`
  exists and contains `currentBuildInfoStr = 11.21.0...`.
- ~100 MB free in the game folder for backup.

## Commands

```powershell
cd <agent_kit>
py -m pip install -r requirements.txt
py bootstrap.py --game "D:\Program Files (x86)\Steam\steamapps\common\World of Tanks Blitz"
```

`bootstrap.py` checks the game version, downloads both mods, verifies SHA-256,
applies the 16 UI YAML edits, converts the reticle DVPL type 4 → type 2, merges
the sound `SoundbanksInfo` with the local micropatch (unless `--skip-overlay`),
writes `payload/` and `manifest.json`. Expected: **58 files** (16 UI, 5 sound,
37 reticle).

Then:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Both must exit `0`. If the overlay hash differs (micropatch changed):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -SkipOverlay
```

Sound and reticle still install; only the merged overlay metadata is skipped.

## Agent checklist

1. `Get-Process wotblitz` returns nothing.
2. Game version is `11.21.0`; otherwise stop — this kit is version-pinned.
3. `py bootstrap.py ...` exits `0`; `manifest.json` has 58 files.
4. `install.ps1 -DryRun` exits `0` (all original hashes match).
5. `install.ps1` exits `0`; backup directory exists.
6. Do not copy files manually; do not launch the game during install.
7. If the game was reinstalled at 11.21.0, the same kit works.
8. After a game update: stop; the kit must be rebuilt for the new version.

## Verify in game

- Lobby: badges faint, promo/event banners and News entry gone, shop button present.
- Battle: solid WoT-style reticle; new gun sounds.
- If a reticle variant is not selected, choose one of the three in settings.

## Uninstall

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall.ps1
```

Restores Data and the overlay file from the latest backup. `-DryRun` checks
without writing.

## Ban / safety

Only sound, custom UI and custom reticle — all explicitly allowed by the WG
Modification Policy. No DLL, injection, memory patching, automation, aim assist,
weak-spot logic, stat changes or battle HUD markers. The installer refuses
executables and categories other than `ui`/`sound`/`reticle`.

Not affiliated with Wargaming/Lesta. Mods are third-party; policy can change.
