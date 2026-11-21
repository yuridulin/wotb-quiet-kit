#!/usr/bin/env python3
"""Package only the small agent kit (no downloads/payload/manifest)."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "dist" / "quiet_11.21_agent"
ZIP = ROOT.parent / "dist" / "quiet_11.21_agent.zip"
INCLUDE = (
    "AGENT.md",
    "README.md",
    "bootstrap.py",
    "requirements.txt",
    "install.ps1",
    "uninstall.ps1",
    "lib.ps1",
    "ui_src",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for rel in INCLUDE:
        src = ROOT / rel
        dst = OUT / rel
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    sums = []
    for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
        sums.append(f"{sha256(path)}  {path.relative_to(OUT).as_posix()}")
    (OUT / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    (OUT / "VERSION.txt").write_text(
        "package=quiet_11.21\ngame=11.21.0\n"
        "sound=Gun Sounds from World of Tanks / DeltBlitz\n"
        "reticle=WoT-style crosshair customization / DorTep\n"
        "ui_patch=16 YAML\n",
        encoding="utf-8",
    )

    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in OUT.rglob("*") if p.is_file()):
            zf.write(path, f"quiet_11.21_agent/{path.relative_to(OUT).as_posix()}")
    print(f"{ZIP} ({ZIP.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
