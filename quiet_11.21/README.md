# quiet_11.21 — звук и тихий лобби-UI для WoT Blitz

Пакет для **World of Tanks Blitz 11.21.0 (PC, Steam/Wargaming)**:

- звуки орудий из WoT PC — профиль DeltBlitz «Gun Sounds from World of Tanks» (альтернатива Maddox лежит рядом);
- прицел WoT-style: сплошной круг и перекрестие (мод DorTep);
- бейджи уведомлений приглушены до 15%;
- скрытые баннеры предложений и промо;
- скрытый пункт «Новости»; магазин остаётся доступным.

Ставится и снимается PowerShell-скриптами с проверкой хешей и резервной копией.

## Требования

- Windows, PowerShell 5.1+.
- Игра **11.21.0**. На другой версии установщик откажется работать: хеши оригиналов не совпадут.
- Игра закрыта: процесс `wotblitz.exe` не должен быть запущен.
- Свободно ~100 МБ на диске игры под резервную копию.

Пакет меняет только клиентские ресурсы. Игровое преимущество не даёт; по политике WG это косметика.

## Установка

```powershell
cd D:\Life\blitz\wotb_mods\quiet_11.21
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Если игра не найдена автоматически:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -GamePath "D:\Program Files (x86)\Steam\steamapps\common\World of Tanks Blitz"
```

Сначала можно проверить без записи:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
```

Полезные ключи:

| Ключ | Что делает |
|---|---|
| `-DryRun` | Проверяет пути, версию и хеши, ничего не пишет |
| `-GamePath <path>` | Явный путь к папке игры |
| `-OverlayPath <path>` | Путь к micropatch-папке; по умолчанию `%LOCALAPPDATA%\wotblitz\packs` |
| `-SkipSound` | Только UI и прицел |
| `-SkipUI` | Без лобби-UI, звук и прицел остаются |
| `-SkipReticle` | Без прицела |
| `-SkipOverlay` | Не трогать `packs\WwiseSound\SoundbanksInfo.json.dvpl`; полезно, если micropatch у друга отличается |
| `-Force` | Разрешает установку поверх изменённых файлов; для осознанного использования |

Установщик сначала проверяет **все** файлы. Если хотя бы один оригинал не совпал с эталоном 11.21.0, он ничего не меняет.

## Что именно меняется

| Категория | Файлов | Содержимое |
|---|---:|---|
| Звук (Data) | 4 | `WwiseSound/weapon.bnk.dvpl`, `weapon_basic.bnk.dvpl`, `SoundbanksInfo.json` + `.dvpl` (профиль DeltBlitz) |
| Micropatch overlay | 1 | `packs/WwiseSound/SoundbanksInfo.json.dvpl` — метаданные overlay + банки оружия профиля |
| UI | 16 | Бейджи — `opacity: 0.15`; баннеры и пункт «Новости» — `visible: false` |
| Прицел | 37 | WoT-style: сплошной круг, перекрестие, маркеры; `UI/Screens/Battle/Aims/*` + `Gfx/**/aim/*` |

С профилем Maddox звуковых файлов больше: 516 Data + 1 overlay, всего 570 с прицелом; текущий профиль DeltBlitz — 4 Data + 1 overlay, всего 58.

UI-файлы:

- `UI/Screens3/Lobby/Common/Badge.yaml`, `BadgeHolder.yaml`, `BadgeLive.yaml` — новые бейджи, `opacity: 0.15`;
- `UI/Screens/Lobby/Common/BadgeNew.yaml`, `BindableBadge.yaml` — старые бейджи, `opacity: 0.15`;
- `UI/Screens/Lobby/LobbyHeader.yaml` — иконка непрочитанных новостей, `opacity: 0.15`;
- `UI/Screens3/Lobby/Common/Sidebar/SidebarHangarMenu.yaml` — пункт «Новости»;
- `UI/Screens3/Lobby/Hangar/Offers/PRMP/PrmpOfferBannerWrapper.yaml`, `PrmpOfferBanner.yaml` — промо-баннер в ангаре;
- `UI/Screens3/Lobby/Hangar/Hangar.yaml` — выключены промо-карусель, кнопки событий и stuff-quest;
- `UI/Screens3/Lobby/Promotions/PromotionsWidget.yaml` — промо-виджет;
- `UI/Screens3/Lobby/Hangar/Quests/StuffQuestWidget/StuffQuestWidget.yaml` — карточка события/квеста;
- `UI/Screens3/Lobby/Hangar/HangarAdvertisingButton.yaml` — кнопка видео-рекламы;
- `UI/Screens3/Lobby/Shop/PremShopBanner.yaml` — баннер премиум-магазина;
- `UI/Screens/Hangar/Actionbanner_big1.yaml`, `Actionbanner_big2.yaml` — старые акционные баннеры.

Бейджи не удалены: у них выставлена прозрачность 15%, поэтому красные кружки и счётчики остаются, но не привлекают внимание. Баннеры и точки входа скрыты через `visible: false`, без удаления логики: элементы не рисуются и не должны ловить ввод, но сервер и клиентский код продолжают их создавать.

`SoundbanksInfo.json.dvpl` в micropatch-папке перекрывает `Data`-версию. Сборщик берёт метаданные overlay (там есть события текущего ивента) и заменяет в них банки `weapon`/`weapon_basic` на версии профиля. Итог ставится и в `Data`, и в `packs`; перед заменой overlay-файл уходит в backup.

### Прицел

Мод [WoT-style crosshair customization](https://forblitz.ru/en/mods/scopes/wot-style-crosshair-customization/21720) (DorTep, WG-архив):

- сплошной круг разброса вместо пунктирного;
- перекрестие/маркеры в стиле WoT;
- три варианта прицела и иконки выбора;
- меняются только `UI/Screens/Battle/Aims/*` и `Gfx/**/aim/*`; логика, разброс и броня не тронуты.

Архив ForBlitz был в DVPL type 4 (28-байтный заголовок + LZ4). Для WG 11.21.0 он сконвертирован в стандартный type 2 без изменения содержимого; YAML-версии (`161`/`159`) совпадают с игрой. Исходники лежат в `vendor/reticle`.

Если после установки прицел не изменился — проверь выбор прицела в настройках: мод меняет все три варианта, но активный слот должен быть один из них.

### Что не меняется

- Боевой HUD, критические бейджи, урон и маркеры — не тронуты.
- Прицел изменён только визуально (отдельный мод): сплошной круг/перекрестие, без aim assist и weak-spot логики.
- Диалоги и всплывающие окна — не тронуты. В этом пакете их нет.
- Уведомления могут продолжать звучать: бейдж приглушён до 15%, а не удалён.
- Пункт «Новости» скрыт как точка входа; магазин доступен, но его промо-баннеры скрыты.
- 3D-экран DUNE в сцене ангара — это объект карты, не UI-баннер; он не тронут.
- Кнопки «+» у валют/премиума — отдельные покупки, не тронуты.

## Проверка после установки

1. Запустить игру.
2. Проверить лобби: бейджи очень бледные (15%), кнопка магазина на месте, пункта «Новости» и промо-баннера нет.
3. Зайти в бой: звук выстрелов должен быть новым, прицел — сплошной круг с перекрестием. В логе не должно быть ошибок `Wwise`/soundbank/UI.
4. Если игра падает или UI не загружается — сразу снять мод (ниже).

Свежий лог: `%LOCALAPPDATA%\wotblitz\DAVAProject\blitz-logs_*.txt`.

## Удаление

```powershell
cd D:\Life\blitz\wotb_mods\quiet_11.21
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall.ps1
```

Скрипт берёт последнюю резервную копию из:

```text
<Game>\_mod_backup\quiet_11.21\<timestamp>\
```

Можно указать конкретную:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall.ps1 -BackupDir "<Game>\_mod_backup\quiet_11.21\20261121-140000"
```

Проверка без записи:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\uninstall.ps1 -DryRun
```

`-Force` — если файлы менялись после установки и нужно всё равно восстановить backup.
`-RemoveBackup` — удалить папку backup после успешного восстановления.
Overlay-файл из `packs\WwiseSound` тоже восстанавливается из backup.

## Обновление игры

Пакет воспроизводим: UI-исходники лежат в `src/`, звук — в `vendor/sound_mod`, манифест и payload пересобираются скриптом. Руками файлы игры не правятся.

1. Закрыть игру.
2. После обновления — Steam → «Проверить целостность файлов», чтобы вернуть ванильные файлы. Если мод ещё цел, можно сначала `uninstall.ps1`.
3. Скачать sound-мод под новую версию и **полностью заменить** `vendor/sound_mod`. `profile.json` в этой папке должен содержать `gameVersion` новой версии.
4. Если в новой версии изменились UI-пути, поправить `src/Data/...`; сборщик упадёт, если исходник перестал соответствовать игре.
5. Пересобрать и поставить:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\update.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\update.ps1
```

`update.ps1` сверяет версию игры с `vendor/sound_mod/profile.json` и `vendor/reticle/profile.json`, пересобирает payload и вызывает `install.ps1`. Если версии не совпали — останавливается до записи. Для нестандартного пути: `-GamePath` и `-OverlayPath`.

Если старый мод ещё установлен, `install.ps1` откажется перезаписывать: сначала `uninstall.ps1` (или Steam verify). `-Force` — только осознанно.

## Важно

- **Steam «Проверить целостность файлов»** вернёт оригиналы и сломает хеши. После этого `uninstall.ps1` может отказаться работать без `-Force`; резервная копия всё равно лежит в `_mod_backup`.
- Обновление игры перезапишет файлы и/или изменит версию. Перед обновлением лучше снять мод.
- Скрытые баннеры событий убирают входы в акции; если понадобится конкретная акция — снять мод.
- Скрытые «Новости» — это ещё и компенсации/подарки. Если они нужны, ставьте с `-SkipUI` или правьте список файлов.
- Звуковой мод — сторонний: [Gun Sounds from World of Tanks](https://blitz-mods.com/mod/gun-sounds/gun-sounds-from-world-of-tanks-301), автор DeltBlitz. Альтернативный профиль Maddox лежит в `vendor/sound_mod_maddox`. Пакет не связан с Wargaming/Lesta.

## Бан-риск

Коротко: по опубликованным правилам WG пакет укладывается в разрешённые моды, но гарантии на 100% нет — решение всегда за администрацией.

- [Modification Policy for WoT Blitz](https://wargaming.net/support/en/products/wotb/article/19038) прямо разрешает **Sound Mods**, **Custom UI Elements** и **Custom Reticle**, если мод не даёт игрового преимущества. Запрещены хит-скины модулей, «лазер», маркеры попаданий по невидимым — этого в пакете нет.
- [EULA](https://legal.wargaming.net/en/user-documents/eula/end-user-license-agreement/view), п. 12.1(l), запрещает моды, **кроме явно разрешённых Wargaming**. Политика выше и есть это разрешение для звука, UI и прицела.
- [Game Rules](https://legal.wargaming.net/en/user-documents/game-rules/game-rules-wotb), п. 1.19 и 2.1.6, наказывают запрещённые моды, ботов, макросы и автоматизацию. Пакет ничего из этого не делает.

Что пакет **не** делает:

- не внедряет DLL, не патчит память, не перехватывает сеть;
- не автоматизирует ввод и не играет за игрока;
- не меняет броню, урон, обзор, маскировку, баллистику;
- не трогает боевой HUD, прицел, маркеры попаданий и засвета;
- не показывает невидимых противников и не даёт тактической информации.

Установщик дополнительно отказывается ставить файлы с расширениями `.exe`, `.dll`, `.bat`, `.cmd`, `.ps1`, `.vbs`, `.js` и любые категории, кроме `ui`/`sound`/`reticle`. Overlay-правка — это только `SoundbanksInfo.json.dvpl` (звуковые метаданные), не игровая логика.

Проверка по файлам: UI изменён только прозрачностью бейджей (`opacity: 0.15`), скрытием баннеров и пункта «Новости» (`visible: false`), `showPromotions=false`. Звук — Wwise-банки `weapon`/`weapon_basic` и `SoundbanksInfo` (в профиле Maddox XML меняет только `<effects>`/`soundPC/NPC`/`soundCannonade`). Прицел — только YAML/текстуры `UI/Screens/Battle/Aims` и `Gfx/**/aim`; без aim assist, weak-spot логики и изменения разброса. Статов, брони, урона и логики нет.

Остаточные риски:

- мод сторонний: файлы взяты с blitz-mods, внутри только `.dvpl`/`.xml`/`.bnk`/`.json`, без `.exe`/`.dll`;
- звуковой мод меняет сэмплы и затухание; WG относит звуковые моды к разрешённым, но это самый «серый» пункт. Для минимального риска ставьте с `-SkipSound`;
- WG может изменить политику или включить проверку файлов в будущем; перед обновлением лучше снять мод;
- ReShade уже стоял до пакета; мы его не трогали. Это отдельный внешний риск, не связанный с `Data`.

Это не юридическая консультация. Если нужен режим «только UI, без звука»: `install.ps1 -SkipSound`; если нужен «только звук»: `-SkipUI`.

### Что нашлось по публичным sound-модам

- [Gun Sounds from World of Tanks](https://blitz-mods.com/mod/gun-sounds/gun-sounds-from-world-of-tanks-301) — 25 252 скачивания, 4.8, обновлён 13.04.26. **Именно этот профиль установлен сейчас** (DeltBlitz, WG, bank 135).
- [Gun sounds from PC WoT [11.21]](https://blitz-mods.com/mod/gun-sounds/from-pc-wot-10-4-54) — 74 086 скачиваний, 4.3, обновлён 15.10.26. Альтернативный профиль Maddox.
- [STEAM & WGC WoT PC sound modpack](https://www.blitz-mods.com/mod/modpacks/steam-wgc-wot-pc-modpack-for-world-of-tanks-blitz-285) — 40 730 скачиваний, 4.7, обновлён 30.07.26.
- [ForBlitz: 177 sound-модов](https://forblitz.ru/en/mods) в каталоге; у [GSM Lite](https://forblitz.ru/mods/battle-sounds/gsm-lite-global-sound-mod/21506) 432 комментария, у [Old gun sounds](https://forblitz.ru/mods/battle-sounds/old-gun-sounds/13768) 252k просмотров. Свежий комментарий к Old gun sounds: «11.21 вг работает».
- Reddit: [2020](https://www.reddit.com/r/WorldOfTanksBlitz/comments/kb0e1h/can_i_use_sound_mods/) и [2022](https://www.reddit.com/r/WorldOfTanksBlitz/comments/w3i67k/getting_banned_for_sound_mod/) — звуковые моды не банят; [2025](https://www.reddit.com/r/WorldOfTanksBlitz/comments/1mn6h4f/how_to_install_sound_and_hudvisual_mods_for_pc/) — актуальная инструкция по установке.
- В найденных комментариях и тредах **нет сообщений о бане именно за звук**; жалобы в основном на совместимость, тихие голоса, чёрный экран или вылеты.

Публичность и скачивания — не гарантия, но это массовая практика, совпадающая с официальной политикой. Историческая паника 2018 года была связана с тогдашним «детектором модов»; позже в сообществе объяснили, что skins/sounds не собирались запрещать, а политика 2024 года это подтверждает.

## Поделиться

**Последний вариант:** <https://github.com/yuridulin/wotb-quiet-kit/releases/latest>  
Перед установкой агент должен проверить latest release и взять оттуда `quiet_11.21_agent.zip`; версия в релизе должна совпадать с игрой.

**Для агента (единственный вариант для шаринга, ~47 КБ):**

```text
dist\quiet_11.21_agent.zip
```

Внутри `AGENT.md`, `bootstrap.py`, `requirements.txt`, `ui_src/` (16 YAML), `install.ps1`, `uninstall.ps1`, `lib.ps1`. Больших файлов нет: `bootstrap.py` сам качает публичные sound/reticle-моды по URL из `AGENT.md`, проверяет SHA-256, применяет UI-патч и собирает `payload/` + `manifest.json` на месте.

```powershell
py -m pip install -r requirements.txt
py bootstrap.py --game "D:\...\World of Tanks Blitz"
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

Готовый payload/архивы модов **не передаются**. Python нужен только как локальный инструмент сборки DVPL; `install.ps1` работает без него.

Другу: закрыть игру, распаковать kit, запустить `install.ps1 -DryRun`, затем `install.ps1`. Если другой micropatch — `-SkipOverlay`. Агенту — `AGENT.md`.

После обновления игры пакет `11.21.0` не подойдёт: обновить `vendor/sound_mod` и `vendor/reticle` под новую версию, выполнить `tools/update.ps1`, затем снова `tools/make_dist.py` и пересобрать agent kit.

## Состав пакета

```text
quiet_11.21/
  install.ps1              установка
  uninstall.ps1            восстановление
  lib.ps1                  поиск игры, хеши, проверки
  manifest.json            список файлов + SHA-256 оригиналов и патчей
  payload/Data/            файлы для Data
  payload/Overlay/         merged SoundbanksInfo для micropatch packs
  src/Data/                отредактированные YAML-исходники UI
  vendor/reticle/          WoT-style прицел + profile.json
  vendor/sound_mod/        текущий профиль DeltBlitz + profile.json
  vendor/sound_mod_maddox/ альтернативный профиль Maddox + profile.json
  tools/build_payload.py   пересборка payload + merge SoundbanksInfo
  tools/update.ps1         проверка версии, пересборка и установка
```

Пересборка:

```powershell
python tools\build_payload.py
```

Скрипт проверит DVPL, пересоберёт UI с тем же типом сжатия, смержит `SoundbanksInfo` с micropatch и обновит `manifest.json`.
