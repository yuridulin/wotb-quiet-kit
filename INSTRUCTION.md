# WoT Blitz 11.21.0 — косметический набор

## Идея

Собрать клиентский косметический набор для **World of Tanks Blitz 11.21.0
(PC, Steam/Wargaming)**:

- звуки орудий из WoT PC;
- прицел в стиле WoT: сплошной круг + перекрестие;
- тихое лобби: бейджи уведомлений почти прозрачные, промо/событийные баннеры
  и пункт «Новости» скрыты, магазин остаётся доступным.

Всё меняется только на клиенте. Никакой игровой логики, статов, HUD-маркеров,
aim assist или автоматизации. Это разрешённые WG категории: sound, custom UI,
custom reticle.

Пакет привязан к версии игры. На другой версии YAML/DVPL и sound-банки могут
не совпасть; тогда нужен новый набор, а не «натягивание» старого.

## Подходы

### 1. Звук

Источник: публичный WG-архив «Gun Sounds from World of Tanks» (DeltBlitz).
Альтернатива — «Gun sounds from PC WoT» (Maddox).

Что делать:

- заменить в `Data/WwiseSound` банки `weapon.bnk.dvpl`,
  `weapon_basic.bnk.dvpl` и `SoundbanksInfo.json`/`.dvpl`;
- в micropatch-папке `%LOCALAPPDATA%\wotblitz\packs\WwiseSound` проверить
  `SoundbanksInfo.json.dvpl`: она перекрывает `Data`. Взять её JSON как основу
  и заменить в нём записи банков `weapon`/`weapon_basic` на записи из
  sound-мода, чтобы не потерять события текущего ивента;
- если overlay-версия не совпадает или не нужна — не трогать overlay,
  оставить только `Data`; основные звуки будут работать, часть
  дополнительных слоёв может отсутствовать;
- сохранить оригиналы и проверить, что после замены игра инициализирует Wwise
  без ошибок soundbank.

Не смешивать файлы разных версий игры: Wwise bank ID и XML sound-события
версионно-зависимы.

### 2. Прицел

Источник: публичный WG-архив «WoT-style crosshair customization» (DorTep).

Что делать:

- заменить `UI/Screens/Battle/Aims/*` и `Gfx/**/aim/*`, включая
  `AimCursor`, `GunSpread`, `aim_camera-marker`, `aim_gun-marker`,
  `custom1/`, `custom2/` и иконки выбора;
- архив ForBlitz приходит в DVPL type 4: 28-байтный заголовок + LZ4-блок.
  Для WG 11.21.0 перепаковать внутренние байты в стандартный DVPL type 2
  (LZ4 + CRC-футер), не меняя содержимое;
- YAML-версии прицела — `161`/`159`; они совпадают с 11.21.0;
- это только визуал: сплошной круг, перекрестие и маркеры. Разброс, броня и
  логика не меняются.

Если после установки прицел старый — проверить, какой из трёх вариантов
выбран в настройках.

### 3. Тихий UI

Бейджи не удалять, а приглушить: добавить `UIOpacityComponent` с
`opacity: 0.15` в корневые прототипы:

- `UI/Screens3/Lobby/Common/Badge.yaml`;
- `BadgeHolder.yaml`;
- `BadgeLive.yaml`;
- `UI/Screens/Lobby/Common/BadgeNew.yaml`;
- `BindableBadge.yaml`;
- `LobbyHeader.yaml` — иконка `UnreadNews`.

Скрыть через `visible: false` / выключить условия:

- `SidebarHangarMenu.yaml` — пункт «Новости»;
- `Hangar.yaml` — `showPromotions=false`, holders событий и stuff-quest;
- `PromotionsWidget.yaml`;
- `StuffQuestWidget.yaml`;
- `PrmpOfferBannerWrapper.yaml`, `PrmpOfferBanner.yaml`;
- `PremShopBanner.yaml`;
- `Actionbanner_big1.yaml`, `Actionbanner_big2.yaml`;
- `HangarAdvertisingButton.yaml`.

`ShopButton.yaml` **не трогать**: магазин должен остаться доступным.

Все правки — только YAML/DDS/Gfx. Логику не удалять: скрытые элементы
продолжают создаваться клиентом, но не рисуются.

### 4. Установка и откат

- Закрыть игру.
- Сделать backup каждого заменяемого файла в
  `<Game>\_mod_backup\quiet_11.21\<timestamp>`; отдельно сохранить overlay
  `packs\WwiseSound\SoundbanksInfo.json.dvpl`.
- Скопировать подготовленные файлы в `Data` и, при необходимости, в
  `%LOCALAPPDATA%\wotblitz\packs`.
- Проверить SHA-256 и запуск игры; в логе
  `%LOCALAPPDATA%\wotblitz\DAVAProject\blitz-logs_*.txt` не должно быть ошибок
  Wwise/UI.
- Откат — вернуть backup; альтернатива — Steam «Проверить целостность файлов»
  (но она не вернёт overlay, его надо восстановить отдельно).

Конкретный инструмент для DVPL/LZ4 — на выбор агента; скрипты не обязательны.

### 5. Версии и обновления

- Проверять latest-инструкцию на GitHub перед работой.
- Держать версию игры и версию sound/reticle-мода совпадающими.
- После обновления игры: заново скачать подходящий sound/reticle, проверить
  YAML-версии и только потом ставить. Старый пакет на новую версию не ставить.
- Если Steam перезаписал файлы — восстановить backup/поставить заново.

## Ссылки

- Latest-инструкция: <https://github.com/yuridulin/wotb-quiet-kit/releases/latest>
- Политика модов WG: <https://wargaming.net/support/en/products/wotb/article/19038>
- EULA: <https://legal.wargaming.net/en/user-documents/eula/end-user-license-agreement/view>
- Game Rules: <https://legal.wargaming.net/en/user-documents/game-rules/game-rules-wotb>
- Звук (DeltBlitz, WG): <https://blitz-mods.com/mod/gun-sounds/gun-sounds-from-world-of-tanks-301>
- Звук (Maddox, альтернатива): <https://blitz-mods.com/mod/gun-sounds/from-pc-wot-10-4-54>
- Прицел (DorTep, WG-архив): <https://forblitz.ru/en/mods/scopes/wot-style-crosshair-customization/21720>
- Инструменты DVPL: <https://github.com/lanylow/dvpl>, <https://github.com/vorlie/DAVA-Resource-Studio>
- Для сравнения, Lesta-вариант WoT 2.4 (не для WG 11.21.0): <https://forblitz.ru/mods/battle-sounds/gun-sounds-wot2-4/28172>

## Границы

- Никаких DLL, инжекта, патча памяти, сетевых перехватов и автоматизации.
- Никаких hit-skins, «лазера», маркеров попаданий по невидимым, таймеров
  перезарядки, aim assist и weak-spot логики.
- Только sound / custom UI / custom reticle. Это не юридическая консультация:
  правила WG могут измениться, решение о санкциях остаётся за администрацией.
