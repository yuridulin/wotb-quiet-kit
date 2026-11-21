#!/usr/bin/env python3
"""Build the quiet_11.21 payload from edited YAML sources and a sound mod.

DVPL layout (footer, 20 bytes):
    uint32 uncompressed_size
    uint32 compressed_size
    uint32 crc32(payload)
    uint32 compression_type   # 0 = raw, 2 = LZ4 block
    b"DVPL"

The WoTBlitz micropatch overlay (``%LOCALAPPDATA%/wotblitz/packs``) may contain
a newer ``SoundbanksInfo.json.dvpl`` than the base game.  It shadows the Data
copy, so the sound mod's weapon-bank metadata is merged into the overlay copy
instead of only replacing the Data copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

import lz4.block

DVPL_FOOTER = 20
DVPL_MAGIC = b"DVPL"
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GAME = Path(r"D:/Program Files (x86)/Steam/steamapps/common/World of Tanks Blitz")
DEFAULT_OVERLAY = Path.home() / "AppData" / "Local" / "wotblitz" / "packs"
DEFAULT_SOUND = PACKAGE_ROOT / "vendor" / "sound_mod"
DEFAULT_RETICLE = PACKAGE_ROOT / "vendor" / "reticle"
GAME_VERSION = "11.21.0"
RETICLE_PREFIXES = (
    "Gfx/Battle/HUD/aim/",
    "Gfx/Shared/HUD/aim/",
    "Gfx/Lobby/icons/icon_aim_",
    "UI/Screens/Battle/Aims/",
)
DEFAULT_SOUND_META = {
    "name": "Unknown sound mod",
    "version": "unknown",
    "gameVersion": GAME_VERSION,
    "author": "unknown",
    "source": "",
}


def read_profile(sound: Path) -> dict:
    profile_path = sound / "profile.json"
    if not profile_path.exists():
        return dict(DEFAULT_SOUND_META)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    for key, value in DEFAULT_SOUND_META.items():
        profile.setdefault(key, value)
    return profile

WEAPON_BANKS = ("weapon", "weapon_basic")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_dvpl(path: Path) -> tuple[bytes, int]:
    raw = path.read_bytes()
    if len(raw) < DVPL_FOOTER or raw[-4:] != DVPL_MAGIC:
        raise ValueError(f"{path}: not a DVPL file")
    usize, csize, crc, ctype = struct.unpack("<IIII", raw[-DVPL_FOOTER:-4])
    payload = raw[:-DVPL_FOOTER]
    if len(payload) != csize:
        raise ValueError(f"{path}: compressed size mismatch")
    data = lz4.block.decompress(payload, uncompressed_size=usize) if ctype else payload
    if len(data) != usize or zlib.crc32(payload) & 0xFFFFFFFF != crc:
        raise ValueError(f"{path}: DVPL checksum mismatch")
    return data, ctype


def write_dvpl(path: Path, data: bytes, ctype: int) -> None:
    payload = lz4.block.compress(data, store_size=False) if ctype else data
    footer = struct.pack(
        "<IIII", len(data), len(payload), zlib.crc32(payload) & 0xFFFFFFFF, ctype
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload + footer + DVPL_MAGIC)


def build_ui(src: Path, game: Path, out: Path) -> None:
    for source in sorted((src / "Data").rglob("*.yaml")):
        rel = source.relative_to(src / "Data").as_posix()
        text = source.read_text(encoding="utf-8")
        original = game / "Data" / f"{rel}.dvpl"
        if not original.exists():
            raise FileNotFoundError(f"{rel}: original DVPL not found: {original}")
        data, ctype = read_dvpl(original)
        if text.encode("utf-8") == data:
            raise ValueError(f"{rel}: edited source is identical to the original")
        target = out / "Data" / f"{rel}.dvpl"
        write_dvpl(target, text.encode("utf-8"), ctype)
        back, _ = read_dvpl(target)
        if back != text.encode("utf-8"):
            raise ValueError(f"{rel}: DVPL round-trip mismatch")


def build_sound(sound: Path, out: Path) -> None:
    if not (sound / "WwiseSound").is_dir():
        raise FileNotFoundError(f"{sound}: WwiseSound directory not found")
    for source in sorted(p for p in sound.rglob("*") if p.is_file()):
        rel = source.relative_to(sound).as_posix()
        if rel in ("readme.txt", "profile.json"):
            continue
        target = out / "Data" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if source.suffix == ".dvpl":
            read_dvpl(target)


def build_reticle(reticle: Path, out: Path) -> None:
    if not reticle.is_dir():
        raise FileNotFoundError(f"{reticle}: reticle directory not found")
    for source in sorted(p for p in reticle.rglob("*") if p.is_file()):
        rel = source.relative_to(reticle).as_posix()
        if rel in ("readme.txt", "profile.json"):
            continue
        target = out / "Data" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if source.suffix == ".dvpl":
            read_dvpl(target)


def merge_soundbanks(out: Path, overlay: Path) -> None:
    """Use overlay metadata, but replace weapon banks with the mod's entries."""
    data_json = out / "Data" / "WwiseSound" / "SoundbanksInfo.json"
    data_dvpl = out / "Data" / "WwiseSound" / "SoundbanksInfo.json.dvpl"
    if not data_dvpl.exists():
        raise FileNotFoundError("sound mod has no SoundbanksInfo.json.dvpl")

    data_bytes, data_ctype = read_dvpl(data_dvpl)
    data_json.write_bytes(data_bytes)
    mod = json.loads(data_bytes)

    overlay_dvpl = overlay / "WwiseSound" / "SoundbanksInfo.json.dvpl"
    if not overlay_dvpl.exists():
        print("overlay SoundbanksInfo not found; keeping mod Data metadata")
        return

    ov_data, ov_ctype = read_dvpl(overlay_dvpl)
    merged = json.loads(ov_data)
    mod_banks = {
        bank.get("ShortName"): bank
        for bank in mod["SoundBanksInfo"]["SoundBanks"]
        if bank.get("ShortName") in WEAPON_BANKS
    }
    if set(mod_banks) != set(WEAPON_BANKS):
        raise ValueError("sound mod metadata is missing weapon banks")

    replaced = 0
    for i, bank in enumerate(merged["SoundBanksInfo"]["SoundBanks"]):
        name = bank.get("ShortName")
        if name in mod_banks:
            merged["SoundBanksInfo"]["SoundBanks"][i] = mod_banks[name]
            replaced += 1
    if replaced != len(WEAPON_BANKS):
        raise ValueError(f"overlay metadata has only {replaced} weapon banks")

    def event_count(doc: dict, name: str) -> int:
        for bank in doc["SoundBanksInfo"]["SoundBanks"]:
            if bank.get("ShortName") == name:
                return len(bank.get("IncludedEvents", []))
        return -1

    if event_count(merged, "weapon") != 17:
        raise ValueError("merged weapon bank does not have 17 events")
    if event_count(merged, "event_nc_2026") != 15:
        raise ValueError("merged overlay lost event_nc_2026 events")

    merged_bytes = json.dumps(
        merged, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    data_json.write_bytes(merged_bytes)
    write_dvpl(data_dvpl, merged_bytes, data_ctype)
    write_dvpl(
        out / "Overlay" / "WwiseSound" / "SoundbanksInfo.json.dvpl",
        merged_bytes,
        ov_ctype,
    )
    print("merged SoundbanksInfo: overlay metadata + mod weapon banks")


def collect_entries(payload: Path, game: Path, overlay: Path) -> list[dict]:
    entries: list[dict] = []
    roots = (
        ("data", game / "Data", payload / "Data"),
        ("overlay", overlay, payload / "Overlay"),
    )
    for area, original_root, payload_root in roots:
        if not payload_root.exists():
            continue
        for path in sorted(p for p in payload_root.rglob("*") if p.is_file()):
            rel = path.relative_to(payload_root).as_posix()
            if area == "data" and rel.startswith(RETICLE_PREFIXES):
                category = "reticle"
            elif area == "data" and rel.startswith("UI/"):
                category = "ui"
            else:
                category = "sound"
            original = original_root / rel
            entries.append(
                {
                    "area": area,
                    "path": rel,
                    "category": category,
                    "sha256": sha256(path),
                    "originalExisted": original.exists(),
                    "originalSha256": sha256(original) if original.exists() else None,
                }
            )
    entries.sort(key=lambda e: (e["area"], e["path"]))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--sound", type=Path, default=DEFAULT_SOUND)
    parser.add_argument("--reticle", type=Path, default=DEFAULT_RETICLE)
    parser.add_argument("--src", type=Path, default=PACKAGE_ROOT / "src")
    parser.add_argument("--out", type=Path, default=PACKAGE_ROOT / "payload")
    parser.add_argument("--manifest", type=Path, default=PACKAGE_ROOT / "manifest.json")
    args = parser.parse_args()

    for required in (
        args.game / "Data",
        args.src / "Data",
        args.sound / "WwiseSound",
        args.reticle,
    ):
        if not required.exists():
            print(f"missing: {required}", file=sys.stderr)
            return 1
    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)

    profile = read_profile(args.sound)
    if profile.get("gameVersion") != GAME_VERSION:
        print(
            f"sound mod targets {profile.get('gameVersion')}, package is {GAME_VERSION}",
            file=sys.stderr,
        )
        return 1
    reticle_profile = read_profile(args.reticle)
    if reticle_profile.get("gameVersion") != GAME_VERSION:
        print(
            f"reticle mod targets {reticle_profile.get('gameVersion')}, package is {GAME_VERSION}",
            file=sys.stderr,
        )
        return 1

    build_ui(args.src, args.game, args.out)
    build_sound(args.sound, args.out)
    build_reticle(args.reticle, args.out)
    merge_soundbanks(args.out, args.overlay)
    entries = collect_entries(args.out, args.game, args.overlay)

    manifest = {
        "name": "quiet_11.21",
        "gameVersion": GAME_VERSION,
        "soundMod": {
            "name": profile["name"],
            "version": profile["version"],
            "author": profile["author"],
            "source": profile["source"],
        },
        "reticleMod": {
            "name": reticle_profile["name"],
            "version": reticle_profile["version"],
            "author": reticle_profile["author"],
            "source": reticle_profile["source"],
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": entries,
    }
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    ui = sum(e["category"] == "ui" for e in entries)
    sound = sum(e["category"] == "sound" for e in entries)
    reticle = sum(e["category"] == "reticle" for e in entries)
    overlay = sum(e["area"] == "overlay" for e in entries)
    print(
        f"payload: {len(entries)} files "
        f"({ui} UI, {sound} sound, {reticle} reticle, {overlay} overlay)"
    )
    print(f"manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
