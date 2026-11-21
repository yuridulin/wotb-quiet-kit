# WoT Blitz quiet kit

Cosmetic mod kit for **World of Tanks Blitz 11.21.0 (PC, Steam/Wargaming)**:

- gun sounds from WoT PC (DeltBlitz; Maddox profile available in the source package);
- WoT-style reticle: solid circle + crosshair (DorTep);
- quiet lobby UI: notification badges at 15%, promo/event banners and the News
  entry hidden, shop button kept.

No DLLs, injection, automation, aim assist, stat changes or battle HUD markers.
Sound, custom UI and custom reticle are explicitly allowed by the WG
Modification Policy.

## Latest version

**Check the latest release before installing:**

<https://github.com/yuridulin/wotb-quiet-kit/releases/latest>

Download `quiet_11.21_agent.zip` from the latest release. Each release is pinned
to a game version; the kit refuses a different version instead of guessing.

## For an agent

The agent kit is small (~47 KB). It downloads the public mod archives itself,
verifies their SHA-256, applies the local UI patch, builds `payload/` and
`manifest.json`, then installs with a backup.

```powershell
# game closed, 11.21.0, launched at least once
Expand-Archive quiet_11.21_agent.zip -DestinationPath .
cd quiet_11.21_agent
py -m pip install -r requirements.txt
py bootstrap.py --game "D:\Program Files (x86)\Steam\steamapps\common\World of Tanks Blitz"
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

If the sound site blocks the agent, download the PC-WG archive manually and pass
`--sound-zip`. If the micropatch overlay differs, install with `-SkipOverlay`.
Full details: `agent_kit/AGENT.md`.

## Repository layout

```text
agent_kit/        instruction + bootstrap + UI patch + install scripts
quiet_11.21/      source package, build/dist/update tools, UI source
```

Large artifacts are intentionally not committed: public mod archives are
downloaded by `agent_kit/bootstrap.py`, and generated payloads/backups are
ignored. To rebuild the shareable kit:

```powershell
python agent_kit/make_zip.py
```

To rebuild a direct install zip from a local source package, see
`quiet_11.21/README.md` and `quiet_11.21/tools/make_dist.py`.

## Release

For a new game/mod version:

```powershell
python agent_kit/make_zip.py
git add -A
git commit -m "release: <version>"
git tag v<version>
git push origin main --tags
gh release create v<version> dist/quiet_11.21_agent.zip --title "v<version>" --generate-notes
```

The release asset is the small agent kit; the large payload is not committed or
attached. Bump `GAME_VERSION` in `agent_kit/bootstrap.py` and refresh
`vendor/sound_mod` / `vendor/reticle` before tagging a new game version.

## Safety

- Only cosmetic sound/UI/reticle resources.
- Installer refuses `.exe/.dll/.bat/.cmd/.ps1/.vbs/.js` payloads and categories
  other than `ui`/`sound`/`reticle`.
- Version/hash checks before writing; backup and uninstall included.
- Third-party mods: DeltBlitz (sound), DorTep (reticle). Not affiliated with
  Wargaming or Lesta.

This is not legal advice; WG can change its policy. Do not use prohibited mods.
