#!/usr/bin/env python3
"""Fetch public mods, patch local game files, build payload + manifest.

The large mod archives are downloaded here (or supplied with --sound-zip /
--reticle-zip); only this small kit is transferred.
"""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import os
import re
import shutil
import struct
import sys
import urllib.request
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

import lz4.block

KIT = Path(__file__).resolve().parent
GAME_VERSION = "11.21.0"
SOUND_PAGE = "https://blitz-mods.com/mod/gun-sounds/gun-sounds-from-world-of-tanks-301"
SOUND_SHA256 = "39189653a0f4ebefecc07ae49db2b1529f2344d0331b13b613d718e5df426290"
RETICLE_URL = "https://forblitz.ru/storage/mods/21720/custom-aim-wot_pc_wg.zip"
RETICLE_SHA256 = "7fedda850033cb7de4ece784fefe76dfb31479a0b15b4cb10839e76ee9354047"
RETICLE_PREFIXES = (
    "Gfx/Battle/HUD/aim/",
    "Gfx/Shared/HUD/aim/",
    "Gfx/Lobby/icons/icon_aim_",
    "UI/Screens/Battle/Aims/",
)
SOUND_META = {
    "name": "Gun Sounds from World of Tanks",
    "version": "2026-04-13",
    "author": "DeltBlitz",
    "source": "https://blitz-mods.com/mod/gun-sounds/gun-sounds-from-world-of-tanks-301",
}
RETICLE_META = {
    "name": "WoT-style crosshair customization",
    "version": "2026-04-13",
    "author": "DorTep",
    "source": "https://forblitz.ru/en/mods/scopes/wot-style-crosshair-customization/21720",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_game(explicit: str) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("WOTB_GAME_PATH"):
        candidates.append(Path(os.environ["WOTB_GAME_PATH"]))
    gp = KIT / "gamepath.txt"
    if gp.exists():
        candidates.append(Path(gp.read_text(encoding="utf-8").strip()))

    steam_roots = [
        Path(os.environ.get(program, "")) / "Steam"
        for program in ("ProgramFiles(x86)", "ProgramFiles")
        if os.environ.get(program)
    ]
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            steam_roots.append(Path(steam_path))
    except Exception:
        pass

    for steam in steam_roots:
        if not steam:
            continue
        candidates.append(steam / "steamapps" / "common" / "World of Tanks Blitz")
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            text = vdf.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r'"path"\s+"([^"]+)"', text):
                library = Path(match.group(1).replace("\\\\", "\\"))
                candidates.append(library / "steamapps" / "common" / "World of Tanks Blitz")

    candidates += [
        Path(r"D:/Program Files (x86)/Steam/steamapps/common/World of Tanks Blitz"),
        Path(r"C:/Program Files (x86)/Steam/steamapps/common/World of Tanks Blitz"),
        Path(r"C:/Program Files/Steam/steamapps/common/World of Tanks Blitz"),
        Path(r"C:/Games/World of Tanks Blitz"),
        Path(r"D:/Games/World of Tanks Blitz"),
    ]
    for candidate in candidates:
        if (candidate / "Data" / "WwiseSound").is_dir():
            return candidate
    return None


def detect_game_version() -> str | None:
    log_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "wotblitz" / "DAVAProject"
    logs = sorted(
        log_dir.glob("blitz-logs_*.txt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if log_dir.exists() else []
    for log in logs:
        text = log.read_text(encoding="utf-8", errors="ignore")
        match = re.search(
            r"currentBuildInfoStr\s*=\s*([0-9]+\.[0-9]+\.[0-9]+)", text
        )
        if match:
            return match.group(1)
    return None


def read_dvpl(raw: bytes) -> tuple[bytes, int]:
    if len(raw) < 20 or raw[-4:] != b"DVPL":
        raise ValueError("not a DVPL file")
    usize, csize, crc, ctype = struct.unpack("<IIII", raw[-20:-4])
    payload = raw[:-20]
    if ctype == 0:
        inner = payload
    elif ctype == 2:
        inner = lz4.block.decompress(payload, uncompressed_size=usize)
    elif ctype == 4:
        # ForBlitz type 4: 28-byte header, then an LZ4 block. Its CRC field
        # does not cover the same bytes as type 0/2, so validate only the size.
        inner = lz4.block.decompress(payload[28:], uncompressed_size=usize)
        if len(inner) != usize:
            raise ValueError("DVPL size mismatch")
        return inner, ctype
    else:
        raise ValueError(f"unsupported DVPL type {ctype}")
    if len(inner) != usize or zlib.crc32(payload) & 0xFFFFFFFF != crc:
        raise ValueError("DVPL checksum mismatch")
    return inner, ctype


def write_dvpl(data: bytes, ctype: int = 2) -> bytes:
    payload = lz4.block.compress(data, store_size=False) if ctype else data
    footer = struct.pack(
        "<IIII", len(data), len(payload), zlib.crc32(payload) & 0xFFFFFFFF, ctype
    )
    return payload + footer + b"DVPL"


def download(url: str, dest: Path, opener=None, referer: str | None = None) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0"}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with (opener or urllib.request.build_opener()).open(request) as response:
        data = response.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return data


def acquire_sound(local: Path | None) -> Path:
    downloads = KIT / "downloads"
    dest = downloads / "gun-sounds-wot-pc-wg.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if local:
        shutil.copy2(local, dest)
    else:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(jar),
            urllib.request.HTTPRedirectHandler(),
        )
        page_url = SOUND_PAGE + "/download/pc-wg"
        html = download(page_url, downloads / "sound-page.html", opener).decode(
            "utf-8", "replace"
        )
        match = re.search(
            r"download/pc-wg/file\?_token=[A-Za-z0-9]+&(?:amp;)?ordinal=[0-9]+", html
        )
        if not match:
            raise SystemExit(
                "Cannot find sound download token. Download it manually and pass --sound-zip."
            )
        token = match.group(0).replace("&amp;", "&")
        download(SOUND_PAGE + "/" + token, dest, opener, referer=SOUND_PAGE)
    data = dest.read_bytes()
    if sha256(data) != SOUND_SHA256:
        raise SystemExit(f"sound archive hash mismatch: {sha256(data)}")
    if not zipfile.is_zipfile(dest):
        raise SystemExit("sound archive is not a zip")
    return dest


def acquire_reticle(local: Path | None) -> Path:
    downloads = KIT / "downloads"
    dest = downloads / "custom-aim-wot_pc_wg.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if local:
        shutil.copy2(local, dest)
    else:
        download(RETICLE_URL, dest)
    data = dest.read_bytes()
    if sha256(data) != RETICLE_SHA256:
        raise SystemExit(f"reticle archive hash mismatch: {sha256(data)}")
    if not zipfile.is_zipfile(dest):
        raise SystemExit("reticle archive is not a zip")
    return dest


def extract_sound(zip_path: Path) -> tuple[dict[str, bytes], dict]:
    wanted = {
        "WwiseSound/weapon.bnk.dvpl",
        "WwiseSound/weapon_basic.bnk.dvpl",
        "WwiseSound/SoundbanksInfo.json.dvpl",
    }
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        missing = wanted - names
        if missing:
            raise SystemExit(f"sound archive missing: {sorted(missing)}")
        for name in wanted:
            raw = zf.read(name)
            read_dvpl(raw)
            files[name] = raw
        meta_raw, _ = read_dvpl(zf.read("WwiseSound/SoundbanksInfo.json.dvpl"))
        meta = json.loads(meta_raw)
    return files, meta


def extract_reticle(zip_path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if not name.endswith(".dvpl"):
                continue
            inner, _ = read_dvpl(zf.read(name))
            files[name] = write_dvpl(inner, 2)
    return files


def merge_sound_metadata(
    meta: dict, overlay: Path, skip_overlay: bool
) -> tuple[bytes, bytes | None]:
    merged = json.loads(json.dumps(meta))
    overlay_bytes: bytes | None = None
    overlay_file = overlay / "WwiseSound" / "SoundbanksInfo.json.dvpl"
    if not skip_overlay and overlay_file.exists():
        ov_raw, _ = read_dvpl(overlay_file.read_bytes())
        ov = json.loads(ov_raw)
        mod_banks = {
            bank["ShortName"]: bank
            for bank in merged["SoundBanksInfo"]["SoundBanks"]
            if bank.get("ShortName") in ("weapon", "weapon_basic")
        }
        replaced = 0
        for index, bank in enumerate(ov["SoundBanksInfo"]["SoundBanks"]):
            if bank.get("ShortName") in mod_banks:
                ov["SoundBanksInfo"]["SoundBanks"][index] = mod_banks[bank["ShortName"]]
                replaced += 1
        if replaced != len(mod_banks):
            raise SystemExit("overlay metadata has no weapon banks")
        merged = ov
        overlay_bytes = write_dvpl(
            json.dumps(merged, ensure_ascii=False, separators=(",", ":")).encode(),
            2,
        )
    data_bytes = json.dumps(merged, ensure_ascii=False, separators=(",", ":")).encode()
    return data_bytes, overlay_bytes


def build_ui(game: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    source_root = KIT / "ui_src" / "Data"
    for source in sorted(source_root.rglob("*.yaml")):
        rel = source.relative_to(source_root).as_posix()
        original = game / "Data" / f"{rel}.dvpl"
        if not original.exists():
            raise SystemExit(f"missing original UI file: {original}")
        _, ctype = read_dvpl(original.read_bytes())
        files[f"{rel}.dvpl"] = write_dvpl(source.read_text(encoding="utf-8").encode(), ctype)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="")
    parser.add_argument("--sound-zip", type=Path)
    parser.add_argument("--reticle-zip", type=Path)
    parser.add_argument("--skip-overlay", action="store_true")
    args = parser.parse_args()

    game = find_game(args.game)
    if not game:
        raise SystemExit("Game not found. Pass --game 'D:\\...\\World of Tanks Blitz'.")
    version = detect_game_version()
    if version != GAME_VERSION:
        raise SystemExit(
            f"Game version is {version or 'unknown'}, package is for {GAME_VERSION}. "
            "Launch the game once or update the kit."
        )

    overlay = Path(os.environ.get("LOCALAPPDATA", "")) / "wotblitz" / "packs"
    sound_zip = acquire_sound(args.sound_zip)
    reticle_zip = acquire_reticle(args.reticle_zip)
    sound_files, sound_meta = extract_sound(sound_zip)
    reticle_files = extract_reticle(reticle_zip)
    ui_files = build_ui(game)
    data_meta, overlay_meta = merge_sound_metadata(
        sound_meta, overlay, args.skip_overlay
    )
    sound_files["WwiseSound/SoundbanksInfo.json"] = data_meta
    sound_files["WwiseSound/SoundbanksInfo.json.dvpl"] = write_dvpl(data_meta, 2)

    payload = KIT / "payload"
    if payload.exists():
        shutil.rmtree(payload)
    data_files = {**ui_files, **sound_files, **reticle_files}
    for rel, data in data_files.items():
        path = payload / "Data" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if overlay_meta is not None:
        rel = "WwiseSound/SoundbanksInfo.json.dvpl"
        path = payload / "Overlay" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(overlay_meta)

    entries = []
    for path in sorted(p for p in payload.rglob("*") if p.is_file()):
        rel_path = path.relative_to(payload)
        area = rel_path.parts[0].lower()
        rel = Path(*rel_path.parts[1:]).as_posix()
        if area == "data" and rel.startswith(RETICLE_PREFIXES):
            category = "reticle"
        elif area == "data" and rel.startswith("UI/"):
            category = "ui"
        else:
            category = "sound"
        original = (game / "Data" if area == "data" else overlay) / rel
        original_bytes = original.read_bytes() if original.exists() else None
        entries.append(
            {
                "area": area,
                "path": rel,
                "category": category,
                "sha256": sha256(path.read_bytes()),
                "originalExisted": original_bytes is not None,
                "originalSha256": sha256(original_bytes) if original_bytes else None,
            }
        )

    manifest = {
        "name": "quiet_11.21",
        "gameVersion": GAME_VERSION,
        "soundMod": SOUND_META,
        "reticleMod": RETICLE_META,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": entries,
    }
    (KIT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    counts = {key: sum(e["category"] == key for e in entries) for key in ("ui", "sound", "reticle")}
    print(f"Game: {game}")
    print(f"Version: {version}")
    print(f"Payload: {len(entries)} files {counts}")
    print("Next:")
    print(r"  powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -DryRun")
    print(r"  powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
