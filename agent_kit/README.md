# quiet_11.21 — agent kit

Latest release: <https://github.com/yuridulin/wotb-quiet-kit/releases/latest>

Small kit for an agent: it downloads the public sound/reticle mods, applies the
local UI patch, builds `payload/` + `manifest.json`, then installs.

Read `AGENT.md` for full requirements, URLs, hashes, paths and checks.

Quick start (game closed, 11.21.0):

```powershell
py -m pip install -r requirements.txt
py bootstrap.py --game "D:\Program Files (x86)\Steam\steamapps\common\World of Tanks Blitz"
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

If the download site blocks the agent, pass `--sound-zip` with the manually
downloaded PC-WG archive. If the overlay hash differs, install with
`-SkipOverlay`.

The large mod archives are not shipped with this kit; `bootstrap.py` fetches
them and verifies their SHA-256. Only `ui_src/` (16 small YAML files) is local.
Python is only the local DVPL build tool, not a mod file.
