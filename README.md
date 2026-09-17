# 🌊 SIA Simulation (`sia-sim`)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Package Manager: uv](https://img.shields.io/badge/uv-fast%20python-purple.svg?logo=astral&logoColor=white)](https://astral.sh/uv)
[![Tests: 238 passed](https://img.shields.io/badge/tests-238%20passed-brightgreen.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Architecture: Hard Boundary](https://img.shields.io/badge/boundary-strict%20SensorFrame-orange.svg)]()
[![MDA Version: 2.2.0](https://img.shields.io/badge/MDA-v2.2.0%20Frozen%20Baseline-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**SIA Simulation** — высокоточный детерминированный физико-сенсорный испытательный стенд (100 Гц) для валидации и верификации ядра предиктивной безопасности яхты **Safety & Intelligence Architecture (SIA) Core**. 

Стенд непрерывно генерирует гидродинамику живого моря, 4-DOF динамику судна, многокомпонентную 3D-аэродинамику парусов и синтетический поток сенсорных наблюдений (`SensorFrame`), тестируя реакцию SIA Core на развитие критических ситуаций (включая сценарий брочинга **SIM-005**) с независимым арбитражем через **Oracle Engine**.

---

## 📌 Содержание

- [🎯 Архитектура и ключевые инварианты](#-архитектура-и-ключевые-инварианты)
- [⚡ Быстрый старт](#-быстрый-старт)
- [💨 3D Аэродинамический движок парусов](#-3d-аэродинамический-движок-парусов-physicssails)
- [⛵ Единый канонический реестр парусов (`CanonicalSailId`)](#-единый-канонический-реестр-парусов-canonicalsailid)
- [🧭 Пресеты живого морского мира (10 World Presets)](#-пресеты-живого-морского-мира-world-presets)
- [🎛 Интерактивный веб-кокпит (Workbench)](#-интерактивный-веб-кокпит-workbench)
- [💬 Диалог активного опроса шкипера (Active Sensing Query Loop)](#-диалог-активного-опроса-шкипера-active-sensing-query-loop)
- [📊 Служебный диагностический терминал логов (Service Logger)](#-служебный-диагностический-терминал-логов-service-logger)
- [📁 Структура репозитория](#-структура-репозитория)
- [🧪 Тестирование и контроль качества](#-тестирование-и-контроль-качества)
- [📜 Лицензия](#-лицензия)

---

## 🎯 Архитектура и ключевые инварианты

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         SIA SIMULATION ENGINE                           │
  │                                                                         │
  │   ┌───────────────────────────┐         ┌───────────────────────────┐   │
  │   │  Living Ocean Environment │  ────▶  │   4-DOF Vessel Dynamics   │   │
  │   │  (Wind/Waves/Sea Current) │         │   (Surge/Sway/Yaw/Roll)   │   │
  │   └───────────────────────────┘         └─────────────┬─────────────┘   │
  │                 │                                     │                 │
  │                 │                       ┌─────────────▼─────────────┐   │
  │                 │                       │  3D Multi-Sail Aerodynamics│  │
  │                 │                       │  (Kinematics / CoE / Rig) │   │
  │                 │                       └─────────────┬─────────────┘   │
  │                 ▼                                     ▼                 │
  │        ┌─────────────────────────────────────────────────────┐          │
  │        │         GroundTruthFrame (Physical Reality)         │          │
  │        └─────────────────────────────────────────────────────┘          │
  │                 │                                     │                 │
  │                 ▼                                     ▼                 │
  │   ┌───────────────────────────┐         ┌───────────────────────────┐   │
  │   │      Sensor Pipeline      │         │       Oracle Engine       │   │
  │   │  (Noise/Drift/IMU/GPS/HW) │         │    (Independent Ground    │   │
  │   │  + Safety Channel Status  │         │      Truth Arbitrage)     │   │
  │   └───────────────────────────┘         └───────────────────────────┘   │
  └─────────────────┼─────────────────────────────────────┼─────────────────┘
                    │ SensorFrame ONLY                    │
                    │ (Hard Boundary: INV-01/02)          │
                    ▼                                     ▼
  ┌───────────────────────────────────┐     ┌───────────────────────────┐
  │             SIA CORE              │     │         EVALUATOR         │
  │   Real-time Predictive Hazard     │────▶│    Autonomous Pass/Fail   │
  │    & Universal Sail Advisor       │     │     Verification Matrix   │
  │   (Broach / Collision / Trim)     │     │    (Safety Margin / FN)   │
  └───────────────────────────────────┘     └───────────────────────────┘
```

### Архитектурные принципы:
1. **Строгая изоляция границы (Hard Boundary — INV-01, INV-02)**:
   - В SIA Core поступает **исключительно** структура `SensorFrame`.
   - Данные `GroundTruthFrame`, состояние гидродинамики, геометрия парусов и внутренние параметры мира **структурно изолированы** и никогда не передаются в SIA Core.
2. **100% Детерминизм и побитовая воспроизводимость**:
   - Дискретный шаг часов симуляции `SimulationClock` ровно **10 мс (100 Гц)**.
   - Нулевая зависимость от системного времени (wall-clock time).
   - Индивидуальные независимые потоки псевдослучайных чисел (PRNG) для каждого сенсорного канала и возмущения.
3. **Классификация каналов безопасности (Safety Channel Status — MDA v2.2 §3.5.2)**:
   - `SensorFrame` маркирует аппаратный статус шины: `WIRED_VERIFIED` (RS-485, гарантия задержки $<20$ мс), `WIRELESS_ADVISORY` (RF 802.15.4, консультативный режим), или `MIXED`.
4. **Многокомпонентная 3D аэродинамика парусов**:
   - Каждый парус рассчитывается как самостоятельное 3D-тело с собственной геометрией, кинематикой гика, поведением при рифлении/скручивании и динамическим положением Центра Парусности ($CoE$).
5. **Единый источник истины для гардероба парусов (Single Source of Truth)**:
   - Все паруса яхты идентифицируются через канонический `CanonicalSailId`, гарантирующий полную совместимость паспорта судна, физического раннера и советника СИА.

---

## ⚡ Быстрый старт

### Требования
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (быстрый менеджер пакетов и виртуальных окружений)

### 1. Установка и запуск
```bash
# Клонирование репозитория
git clone https://github.com/dzentec/SIA_SIM.git
cd SIA_SIM

# Синхронизация зависимостей
uv sync

# Запуск интерактивного Веб-Верстака (Workbench)
uv run sia-sim --workbench --port 8080
```
Откройте в браузере: **`http://localhost:8080`**

### 2. Запуск верификации сценария в CLI
```bash
# Запуск эталонного сценария SIM-005 (Broach Precursor Golden Scenario)
uv run sia-sim --scenario SIM-005

# Запуск с кастомным сидом и длительностью
uv run sia-sim --scenario SIM-005 --seed 42 --duration 20
```

### 3. Запуск полного набора тестов
```bash
uv run pytest -v
```

---

## 💨 3D Аэродинамический движок парусов (`physics/sails/`)

Система рассчитывает паруса как изолированные 3D физические объекты с суммированием аэродинамических векторов и моментов на рангоуте:

```
                ▲ Z (Headsail / Masthead)
                │      /│
                │     / │
                │    /  │ CoE(x,y,z)
                │   /   │    ●──────▶ F_aero (Lift + Drag)
                │  /    │   /
                │ /_____│  /
  ◄─────────────┼─────────────────────────► X (Bow / Stern)
 (Stern)        │ \     │ (Tack)
                │  \____│ (Boom θ_boom)
                ▼ Y (Leeward Outboard)
```

### Ключевые возможности модели:
1. **Кинематика гика и угол атаки**:
   - Угол отклонения гика $\theta_{\text{boom}} = \operatorname{sign}(\text{AWA}) \cdot \min(|\text{AWA}|, \theta_{\text{max}} \cdot (1 - \text{trim\_factor}))$.
   - Эффективный угол атаки потока $\alpha = |\text{AWA}| - |\theta_{\text{boom}}|$. При потравливании шкота ($\text{trim} \to 0$) парус флюгирует по ветру и полностью обессиливается ($\alpha \to 0$).
2. **3D поляры с задержкой срыва (Stall Delay)**:
   - Треугольные паруса малого удлинения удерживают прикрепленный вихревой поток до $\alpha_{\text{stall}} \approx 26^\circ\dots 35^\circ$ (*C.A. Marchaj*, *F. Fossati*).
   - Поддерживаются специализированные поляры для `MAINSAIL`, `GENOA`, `JIB`, `CODE_0`, `GENNAKER`, `SPINNAKER`, `STORM_JIB`.
3. **Динамический Центр Парусности ($CoE$)**:
   - $CoE_y$ смещается на подветренный борт при выходе гика: $CoE_y = y_{\text{tack}} + \frac{2}{3} L_{\text{boom}} \sin(\theta_{\text{boom}})$.
   - $CoE_z$ опускается при рифлении: $CoE_z = z_{\text{tack}} + \frac{1}{3} H_{\text{sail}} \cdot \eta_{\text{reef}}$.
4. **Аэродинамические эффекты вооружения (Rig Interactions)**:
   - **Downwind Blanketing**: Ветровая тень грота при $TWA > 130^\circ$ затеняет передние паруса до $65\%$.
   - **Upwind Slot Effect**: Сопловой эффект между стакселем и гротом на углах $25^\circ\dots 65^\circ$ увеличивает $C_L$ грота до $+15\%$.
5. **Векторные 3D моменты**:
   - Суммарный момент сил рассчитывается как строгое векторное произведение $\vec{M} = \sum (\vec{r}_i \times \vec{F}_i)$, автоматически создавая точные моменты крена ($M_{\text{roll}}$), дифферента ($M_{\text{pitch}}$) и рыскания ($M_{\text{yaw}}$).
6. **Интерфейсы расширения (Decoupled Extension Hooks)**:
   - Внедрены типизированные протоколы: `HullHydrodynamicsHook`, `ApparentWindFeedbackHook`, `WaveSailInteractionHook`, `SailTrimProfileHook`.

---

## ⛵ Единый канонический реестр парусов (`CanonicalSailId`)

Симулятор фиксирует единый реестр парусного гардероба в [`src/sia_sim/contracts/sails.py`](src/sia_sim/contracts/sails.py) (`SAIL_RULES_CATALOG_V1_1`):

| `CanonicalSailId` | Название паруса | Категория | Диапазон ветра ($TWS$) | Оптимальный угол ($TWA$) | Особенности и рифы |
|---|---|---|---|---|---|
| `mainsail_square_top` | **Грот (Square-Top Main)** | Primary / Main | 0–35 kt (Моно) / 0–30 kt (Кат) | $30^\circ–180^\circ$ | Рифы 1-2-3 (15/20/25 kt кат, 18/25/32 kt моно) |
| `solent_jib` | **Солент / Самоповоротный стаксель** | Upwind / Headsail | 12–30 kt (Моно) / 12–28 kt (Кат) | $30^\circ–60^\circ$ | Основной лавировочный парус |
| `genoa_furling` | **Генуя 120–140% на закрутке** | All-round / Headsail | 6–22 kt (Моно) / 6–18 kt (Кат) | $40^\circ–110^\circ$ | На катамаране лимит порывов $MaxGust=22$ kt |
| `code_zero` | **Код 0 (Code 0)** | Light Reacher | 4–15 kt (Моно) / 4–14 kt (Кат) | $45^\circ–90^\circ$ | Гибрид на закрутке, $MaxGust=18$ kt на кате |
| `asymmetric_gennaker_a2` | **Геннакер A2 (Runner)** | Downwind | 6–20 kt (Моно) / 6–18 kt (Кат) | $120^\circ–165^\circ$ | Полные курсы, на кате запрещен $TWA>150^\circ$ |
| `asymmetric_gennaker_a3` | **Геннакер A3/A5 (Reacher)** | Reaching | 14–25 kt (Моно) / 14–24 kt (Кат) | $80^\circ–130^\circ$ | Силовой галфвинд/бакштаг, $MaxGust=28$ kt |
| `parasailor` | **Парасейлор (Крылатый спинакер)** | Cruising Downwind | 8–28 kt | $130^\circ–180^\circ$ | Встроенное крыло, гасит качку, $MaxGust=28$ kt |
| `storm_jib` | **Штормовой стаксель** | Survival / Storm | 28–50 kt | $35^\circ–140^\circ$ | Сверхпрочная ткань для штормования |

---

## 🧭 Пресеты живого морского мира (World Presets)

В симуляторе реализованы **10 реалистичных фоновых состояний океана** (`WORLD_PRESET_CONFIGS`):

| № | Пресет | Категория | Ветер ($TWS$) | Волна ($H_s$) | Период ($T_w$) | Назначение и динамика судна |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Calm Harbour (Mirror)** | Fair Weather | 2.0 kt (1.0 м/с) | 0.1 м | 2.0–3.0 с | Тест маневрирования в марине, швартовка, гладкая вода |
| **2** | **Light Breeze (Smooth)** | Fair Weather | 8.0 kt (4.1 м/с) | 0.5 м | 3.0–4.0 с | Учебный режим, лёгкая рябь, базовые тесты алгоритмов |
| **3** | **Coastal Cruise (Moderate)** | Moderate | 13.0 kt (6.7 м/с) | 1.0 м | 4.0–5.0 с | Стандартный прибрежный круиз, идеальный парусный день (крен ~14°–16°) |
| **4** | **Fresh Breeze (Whitecaps)** | Moderate | 19.0 kt (9.8 м/с) | 1.8 м | 5.0–6.0 с | Энергичный ход, появление белых барашков, активная качка |
| **5** | **Strong Wind (Choppy Sea)** | Heavy | 24.0 kt (12.3 м/с) | 2.5 м | 5.0–7.0 с | Короткая крутая волна, рубеж рифления парусов |
| **6** | **Near Gale (Rough)** | Heavy | 30.0 kt (15.4 м/с) | 3.5 м | 7.0–8.0 с | Сильная качка, брызги, тест работы авторулевого |
| **7** | **Gale Force (Heavy Sea)** | Extreme | 38.0 kt (19.5 м/с) | 5.5 м | 8.0–10.0 с | Настоящий шторм, управление на попутной волне, риск срыва пера |
| **8** | **Storm / Survival** | Extreme | 48.0 kt (24.7 м/с) | 8.5 м | 10.0–12.0 с | Штормование, огромные гребни, тест выживаемости яхты |
| **9** | **Ocean Swell (No Wind)** | Special | 5.0 kt (2.6 м/с) | 2.5 м | 12.0–15.0 с | Длинная океанская зыбь без ветра (тест валкости и бортовой качки) |
| **10** | **Hurricane / Stress Test** | Stress Test | 65.0 kt (33.5 м/с) | 11.0 м | 14.0–20.0 с | Максимальный стресс-тест физики и предиктивных алгоритмов |

---

## 🎛 Интерактивный веб-кокпит (Workbench)

Интерфейс верстака выполнен в архитектуре **Zero-Build Native ES Modules** с темным дизайном матового стекла (Glassmorphism Dark Theme):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 SIA SIMULATION WORKBENCH                               │
├───────────────────────┬────────────────────────────────────────┬───────────────────────┤
│  WORLD PRESET & ENV   │        6-DIAL MARINE CONSOLE           │  2-COL WARDROBE QUERY │
│  [ 10 World Presets ] │  [ AWA / AWS ] [ HEEL ]   [ PITCH ]    │  [Sails]    [Settings]│
│  [ ⚙️ Custom Sea Edit ]│  [ COMPASS   ] [ HEAVE ]  [ SLAM  ]    │  Mainsail    Reef 1/2/3│
├───────────────────────┤                                        ├───────────────────────┤
│  GROUND TRUTH LAB     │  Pitch Rate / Yaw Rate / SOG / HDG     │   SIA CORE ADVISORY   │
│  TWS / TWD / Wave     │  Actuators & Sensors Integrity State   │   Dominant: REDUCE    │
│  True Roll / Pitch    │  Safety Channel: WIRED_VERIFIED        │   Score: 0.95 | Rules │
├───────────────────────┤                                        ├───────────────────────┤
│  VESSEL & RIG DECK    │                                        │   ORACLE EVALUATION   │
│  [ Oceanis 45 | IOR ] │                                        │   Status: PASS        │
│  [ ⛵ Active Rig Cards]│                                        │   Margin: 82%         │
├───────────────────────┴────────────────────────────────────────┴───────────────────────┤
│                     INTERACTIVE TIMELINE & SCENARIO BUILDER (SCRUBBER)                 │
│  [▶ Living Sea] [⏸ Pause] [⏹ Reset] [⏱ 00:01.36] ────────●──────────────────────────── │
│  Tracks: [Wind Gust] [Wave Slam] [IMU Drop] [GPS Loss] [Rudder Stall] [Safety Mode]    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  SERVICE DIAGNOSTICS LOG TERMINAL [ALL] [SIA CORE] [PHYSICS] [SKIPPER] [ORACLE]        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 💬 Диалог активного опроса шкипера (Active Sensing Query Loop)

Ядро СИА знает только паспортный гардероб парусов яхты, но не имеет сенсоров на фалах и шкотах. При резком нарастании крена или риска брочинга СИА инициирует опрос:

1. **Автопауза без таймера обратного отсчета**: Симуляция мягко останавливается, ожидая ввода капитана.
2. **2-колоночный селектор гардероба**:
   - **Колонка 1 (Паруса)**: Отображает доступные паруса яхты (`Mainsail`, `Genoa`, `Solent`, `Code 0`, `Gennaker`, `Storm Jib`).
   - **Колонка 2 (Настройки)**: Мгновенно показывает доступные степени рифления и закрутки для выбранного паруса (`Full`, `Reef 1`, `Reef 2`, `Reef 3`, `Furled`).
3. **Пересчет рекомендаций СИА**: После подтверждения СИА производит переоценку риска и выводит доминантный совет, альтернативные опции и обоснование.
4. **Сохранение времени симуляции**: Применение рекомендаций СИА и рифление парусов никогда не сбрасывают текущее время и курсор симуляции на 0.00с.

---

## 📊 Служебный диагностический терминал логов (Service Logger)

В нижнюю панель верстака интегрирован складной диагностический терминал:
- **Цветовые фильтры подсистем**: `ALL`, `SIA CORE`, `PHYSICS`, `SKIPPER`, `ORACLE`, `SIM RUNNER`.
- **Автоскролл и поиск**: Мгновенный поиск по событиям и временным меткам.
- **Интерактивная шторка**: Переключение высоты (120px ↔ 280px).
- **Экспорт данных**: Выгрузка журналов в форматах **JSON** и **CSV** для отчетов и аудита.

---

## 📁 Структура репозитория

```
src/sia_sim/
├── contracts/          # Строгие Pydantic v2 контракты данных
│   ├── data.py         # SensorFrame, GroundTruthFrame, IMU, GPS, SafetyChannelStatus
│   ├── evaluation.py   # Схемы для OracleResult, RiskAssessment, DecisionPayload
│   ├── sails.py        # Единый реестр парусов (CanonicalSailId) и каталог v1.1
│   └── scenario.py     # Scenario, ScenarioEvent, VesselConfig (с гардеробом)
├── core/               # Ядро симулятора
│   ├── clock.py        # Детерминированные 100 Гц часы (SimulationClock)
│   └── rng.py          # Изолированные детерминированные PRNG-потоки
├── physics/            # Физический и гидродинамический движок
│   ├── dynamics.py     # 4-DOF уравнения движения жесткого тела и качка
│   ├── environment.py  # Моделирование спектра ветра, волн и течений
│   ├── forces.py       # Гидродинамика руля, остойчивость GZ, интеграция SailRig
│   ├── integrator.py   # Численный интегратор RK4
│   └── sails/          # 3D Многопарусный аэродинамический модуль
│       ├── polars.py   # Аэродинамические поляры CL(α), CD(α) с задержкой срыва
│       ├── sail.py     # Изолированный парус: кинематика гика θ_boom, 3D CoE(x,y,z)
│       └── rig.py      # Агрегатор SailRig, резолвер CanonicalSailId, 3D моменты
├── sails/              # Движок рекомендаций парусов (Sail Advisor)
│   └── advisor.py      # Оценка пригодности парусов, порывы, рифы и фильтрация
├── sensors/            # Сенсорный пайплайн синтеза измерений
│   ├── channels.py     # Модели шумов, смещений (bias), дрейфа, задержек и отказов
│   └── pipeline.py     # Сборка 100 Гц SensorFrame с SafetyChannelStatus
├── scenarios/          # Каталог пресетов и золотых сценариев
│   ├── presets.py      # 10 пресетов морского мира (World Presets) и пресеты яхт
│   └── sim005.py       # Золотой сценарий брочинга SIM-005
├── sia/                # Mock-реализация и протоколы интеграции SIA Core
│   └── mock_sia.py     # Эталонное ядро предиктивной безопасности с учетом парусов
├── evaluation/         # Модуль независимой верификации
│   ├── oracle.py       # Расчет истинного риска по Ground Truth
│   └── evaluator.py    # Оценка соответствия решений SIA критериям безопасности
└── workbench/          # Веб-верстак и визуальный кокпит
    ├── server.py       # HTTP API бэкенд + /api/run, /api/scenarios, /api/sails, /api/query-action
    └── static/         # HTML5, Canvas 2D приборы, Zero-Build ES модули
        ├── css/        # Стили Glassmorphism Dark Theme
        └── js/         # app.js, state.js, playback.js, instruments.js, timeline.js, query_loop.js, service_logger.js, modals.js
```

---

## 🧪 Тестирование и контроль качества

Проект покрыт **238 автоматизированными тестами**:

* `test_sail_aerodynamics.py` — Тестирование 3D поляр, кинематики гика, смещения CoE, затенения, щелевого эффекта и протоколов расширения.
* `test_sail_advisor.py` — Тестирование каталога парусов v1.1, катамаранных оверрайдов, безопасных порывов и фильтрации инвентаря.
* `test_sia_boundary.py` — AST-инспекция кода для гарантии отсутствия импортов `GroundTruthFrame` в модулях SIA.
* `test_physics_environment.py` — Тестирование стохастического живого ветра, влияния сидов и детерминированности.
* `test_physics_determinism.py` — Побитовое совпадение физических траекторий при идентичном сиде.
* `test_sensor_determinism.py` — Проверка статистических свойств шумов и независимости каналов.
* `test_simulation_runner.py` — Проверка детерминированного выполнения сценариев SIM-005, BENIGN и удержания курса авторулевым.
* `test_world_presets.py` — Тестирование всех 10 пресетов морского мира на стабильность и отсутствие паразитных событий.
* `test_vessel_presets.py` — Тестирование пресетов яхт и парусных вооружений.
* `test_workbench_server.py` — Верификация эндпоинтов `/api/scenarios`, `/api/run`, `/api/sails` и `/api/query-action`.

```bash
# Проверка типов (Mypy --strict across 83 files)
uv run mypy src tests

# Проверка качества кода (Ruff)
uv run ruff check

# Запуск полного набора тестов (238 passed)
uv run pytest
```

---

## 📜 Лицензия

Проект распространяется под лицензией MIT. Подробности см. в файле [LICENSE](LICENSE).
