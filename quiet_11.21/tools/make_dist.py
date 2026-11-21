#!/usr/bin/env python3
"""Build a minimal shareable install package (no src/vendor/tools)."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
DIST = PACKAGE / "dist"
NAME = "quiet_11.21_install"

README = """# quiet_11.21 — установка

Пакет для **World of Tanks Blitz 11.21.0 (PC, Steam/Wargaming)**.

Внутри:
- звуки орудий DeltBlitz «Gun Sounds from World of Tanks»;
- прицел WoT-style: сплошной круг + перекрестие;
- тихое лобби: бейджи 15%, скрытые баннеры/промо/пункт «Новости», магазин на месте.

## Что нужно

- Windows, PowerShell 5.1+.
- Игра **11.21.0**, закрыта (`wotblitz.exe` не запущен).
- ~100 МБ на диске игры под backup.

## Установка

1. Распаковать архив в любую папку.
2. Проверить без записи:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\\install.ps1 -DryRun
```

3. Установить:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\\install.ps1
```

Если игра не найдена:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\\install.ps1 -GamePath "D:\\Program Files (x86)\\Steam\\steamapps\\common\\World of Tanks Blitz"
```

Если установщик ругается на `packs\\WwiseSound\\SoundbanksInfo.json.dvpl` (у друга другой micropatch):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\\install.ps1 -SkipOverlay
```

Звук и прицел при этом всё равно ставятся; пропускается только merged-метадата overlay.

Можно запускать `install.cmd` двойным кликом, но агенту лучше вызывать `install.ps1` напрямую (без `pause`).

## Удаление

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\\uninstall.ps1
```

Backup: `<Game>\\_mod_backup\\quiet_11.21\\<timestamp>`.

## Важно

- Пакет привязан к 11.21.0. На другой версии установщик откажется: хеши оригиналов не совпадут.
- Steam «Проверить целостность файлов» вернёт оригиналы; после этого ставьте заново.
- Обновление игры: нужен новый пакет/пересборка; этот не ставьте.
- По политике WG разрешены Sound Mods, Custom UI и Custom Reticle. В пакете нет DLL/инжекта/автоматизации, статов, HUD-маркеров и aim assist.
- Моды сторонние: DeltBlitz (звук), DorTep (прицел). Пакет не связан с Wargaming/Lesta.

Проверка целостности файлов: `SHA256SUMS.txt`.
"""

AGENT = """# Для агента

1. Проверь, что игра закрыта: `Get-Process wotblitz` не должен ничего вернуть.
2. `powershell -NoProfile -ExecutionPolicy Bypass -File .\\install.ps1 -DryRun`
3. Если dry-run вернул 0 — `... -File .\\install.ps1`.
4. Exit code 0 = установлено. При ошибке overlay-хеша повтори с `-SkipOverlay`.
5. Не копируй файлы вручную и не запускай игру во время установки.
6. Путь к игре при необходимости: `-GamePath "D:\\...\\World of Tanks Blitz"`.
"""

ATTRIBUTION = """# Attribution

- Sound: **Gun Sounds from World of Tanks**, DeltBlitz — <https://blitz-mods.com/mod/gun-sounds/gun-sounds-from-world-of-tanks-301>
- Reticle: **WoT-style crosshair customization**, DorTep — <https://forblitz.ru/en/mods/scopes/wot-style-crosshair-customization/21720>
- Lobby UI edits: local `src/` in the source package.

Not affiliated with Wargaming or Lesta.
"""

INSTALL_CMD = r"""@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
set RC=%ERRORLEVEL%
echo.
pause
exit /b %RC%
"""

UNINSTALL_CMD = r"""@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1" %*
set RC=%ERRORLEVEL%
echo.
pause
exit /b %RC%
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    payload = PACKAGE / "payload"
    if not payload.is_dir():
        raise SystemExit("payload directory not found")

    out = DIST / NAME
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for name in ("install.ps1", "uninstall.ps1", "lib.ps1", "manifest.json"):
        shutil.copy2(PACKAGE / name, out / name)
    shutil.copytree(payload, out / "payload")

    (out / "README.md").write_text(README, encoding="utf-8")
    (out / "AGENT.md").write_text(AGENT, encoding="utf-8")
    (out / "ATTRIBUTION.md").write_text(ATTRIBUTION, encoding="utf-8")
    (out / "install.cmd").write_text(INSTALL_CMD, encoding="utf-8")
    (out / "uninstall.cmd").write_text(UNINSTALL_CMD, encoding="utf-8")

    version = "\n".join(
        [
            "package=quiet_11.21",
            f"game={manifest['gameVersion']}",
            f"files={len(manifest['files'])}",
            f"sound={manifest['soundMod']['name']} / {manifest['soundMod']['version']}",
            f"reticle={manifest['reticleMod']['name']} / {manifest['reticleMod']['version']}",
        ]
    )
    (out / "VERSION.txt").write_text(version + "\n", encoding="utf-8")

    # Verify every payload file against the manifest before shipping.
    for entry in manifest["files"]:
        area = entry.get("area", "data")
        rel = entry["path"]
        src = out / "payload" / ("Overlay" if area == "overlay" else "Data") / rel
        if not src.exists():
            raise SystemExit(f"missing payload: {rel}")
        if sha256(src) != entry["sha256"]:
            raise SystemExit(f"hash mismatch: {rel}")

    sums = []
    for path in sorted(p for p in out.rglob("*") if p.is_file()):
        rel = path.relative_to(out).as_posix()
        if rel == "SHA256SUMS.txt":
            continue
        sums.append(f"{sha256(path)}  {rel}")
    (out / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")

    zip_path = DIST / f"{NAME}_{manifest['gameVersion']}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in out.rglob("*") if p.is_file()):
            zf.write(path, f"{NAME}/{path.relative_to(out).as_posix()}")

    print(f"folder: {out}")
    print(f"zip:    {zip_path} ({zip_path.stat().st_size / (1024*1024):.1f} MiB)")
    print(f"files:  {len(manifest['files'])} + scripts/docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
