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
5. **Единый источник истины для параметров яхты (Single Source of Truth)**:
   - Геометрия, масса, длина (LOA), ширина (Beam), водоизмещение и парусное вооружение зафиксированы в канонических моделях `BENETEAU_OCEANIS_45_CONFIG` и `DEFAULT_VESSEL_CONFIG` (`Monohull IOR 10.5m`).

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
   - Треугольные паруса малого удлинения удерживают прикрепленный вихревой поток до $\alpha_{\text{stall}} \approx 26^\circ\dots 35^\circ$ (по данным исследований *C.A. Marchaj* и *F. Fossati*).
   - Поддерживаются специализированные поляры для `MAINSAIL`, `GENOA`, `JIB`, `CODE_0`, `GENNAKER`, `SPINNAKER`, `STORM_JIB`.
3. **Динамический Центр Парусности ($CoE$)**:
   - $CoE_y$ смещается на подветренный борт при выходе гика: $CoE_y = y_{\text{tack}} + \frac{2}{3} L_{\text{boom}} \sin(\theta_{\text{boom}})$.
   - $CoE_z$ опускается при рифлении: $CoE_z = z_{\text{tack}} + \frac{1}{3} H_{\text{sail}} \cdot \eta_{\text{reef}}$.
4. **Аэродинамические эффекты вооружения (Rig Interactions)**:
   - **Downwind Blanketing**: Ветровая тень грота при $TWA > 130^\circ$ затеняет передние паруса до $65\%$.
   - **Upwind Slot Effect**: Сопловой эффект между стакселем и гротом на углах $25^\circ\dots 65^\circ$ увеличивает $C_L$ грота до $+15\%$.
5. **Векторные 3D моменты**:
   - Суммарный момент сил рассчитывается как строгое векторное произведение $\vec{M} = \sum (\vec{r}_i \times \vec{F}_i)$, автоматически создавая правильные моменты крена ($M_{\text{roll}}$), дифферента ($M_{\text{pitch}}$) и рыскания ($M_{\text{yaw}}$).
6. **Интерфейсы расширения (Decoupled Extension Hooks)**:
   - Внедрены типизированные протоколы для подключения будущих модулей: `HullHydrodynamicsHook`, `ApparentWindFeedbackHook`, `WaveSailInteractionHook`, `SailTrimProfileHook`.

---

## ⛵ Универсальный справочник парусов v1.1 и Sail Advisor

Симулятор включает универсальный справочник парусного вооружения **`SAIL_RULES_CATALOG_V1_1`** для современных монокорпусов и катамаранов:

| ID паруса | Название | Тип / Категория | Диапазон ветра ($TWS$) | Оптимальный угол ($TWA$) | Особенности и лимиты |
|---|---|---|---|---|---|
| `mainsail_square_top` | **Грот (Square-Top Main)** | Primary / Main | 0–35 kt (Моно) / 0–30 kt (Кат) | $30^\circ–180^\circ$ | Рифы 1-2-3 (15/20/25 kt на кате, 18/25/32 kt на моно) |
| `solent_jib` | **Солент / Самоповоротный стаксель** | Upwind / Headsail | 12–30 kt (Моно) / 12–28 kt (Кат) | $30^\circ–60^\circ$ | Основной лавировочный парус |
| `genoa_furling` | **Генуя 120–140% на закрутке** | All-round / Headsail | 6–22 kt (Моно) / 6–18 kt (Кат) | $40^\circ–110^\circ$ | На катамаране лимит порывов $MaxGust=22$ kt |
| `code_zero` | **Код 0 (Code 0)** | Light Reacher | 4–15 kt (Моно) / 4–14 kt (Кат) | $45^\circ–90^\circ$ | Гибрид на закрутке, $MaxGust=18$ kt на кате |
| `asymmetric_gennaker_a2` | **Геннакер A2 (Runner)** | Downwind | 6–20 kt (Моно) / 6–18 kt (Кат) | $120^\circ–165^\circ$ (Моно) / $110^\circ–150^\circ$ (Кат) | На кате запрещен фордевинд $>150^\circ$, $MaxGust=22$ kt |
| `asymmetric_gennaker_a3` | **Геннакер A3/A5 (Reacher)** | Reaching | 14–25 kt (Моно) / 14–24 kt (Кат) | $80^\circ–130^\circ$ | Силовой галфвинд/бакштаг, $MaxGust=28$ kt |
| `parasailor` | **Парасейлор (Крылатый спинакер)** | Cruising Downwind | 8–28 kt | $130^\circ–180^\circ$ (Моно) / $120^\circ–160^\circ$ (Кат) | Встроенное крыло, гасит качку, $MaxGust=28$ kt |
| `storm_jib` | **Штормовой стаксель** | Survival / Storm | 28–50 kt | $35^\circ–140^\circ$ | Сверхпрочная ткань, работа в шторм |

---

## 🧭 Пресеты живого морского мира (World Presets)

В симуляторе реализованы **10 реалистичных фоновых состояний океана** (`WORLD_PRESET_CONFIGS`):

| № | Пресет | Категория | Ветер ($TWS$) | Волна ($H_s$) | Период ($T_w$) | Назначение и динамика судна |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Calm Harbour (Mirror)** | Fair Weather | 2.0 kt (1.0 м/с) | 0.1 м | 2.0–3.0 с | Тест маневрирования в марине, швартовка, гладкая вода |
| **2** | **Light Breeze (Smooth)** | Fair Weather | 8.0 kt (4.1 м/с) | 0.5 м | 3.0–4.0 с | Учебный режим, лёгкая рябь, базовые тесты алгоритмов |
| **3** | **Coastal Cruise (Moderate)** | Moderate | 13.0 kt (6.7 м/с) | 1.0 м | 4.0–5.0 с | Стандартный прибрежный круиз, идеальный парусный день (крен ~12°) |
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
│  WORLD PRESET & ENV   │        6-DIAL MARINE CONSOLE           │   SKIPPER QUERY LOOP  │
│  [ 10 World Presets ] │  [ AWA / AWS ] [ HEEL ]   [ PITCH ]    │   [ FULL MAIN ][REEF1]│
│  [ ⚙️ Custom Sea Edit ]│  [ COMPASS   ] [ HEAVE ]  [ SLAM  ]    │   [ REEF 2 ]   [STORM]│
├───────────────────────┤                                        ├───────────────────────┤
│  GROUND TRUTH LAB     │  Pitch Rate / Yaw Rate / SOG / HDG     │   SIA CORE ADVISORY   │
│  TWS / TWD / Wave     │  Actuators & Sensors Integrity State   │   Broach Risk: CRIT   │
│  True Roll / Pitch    │  Safety Channel: WIRED_VERIFIED        │   Action: BEAR AWAY   │
├───────────────────────┤                                        ├───────────────────────┤
│  VESSEL & SAIL CONFIG │                                        │   ORACLE EVALUATION   │
│  [ Oceanis 45 | IOR ] │                                        │   Status: PASS        │
│  [ ⚙️ Custom Sails ]   │                                        │   Latency: 42 ms      │
├───────────────────────┴────────────────────────────────────────┴───────────────────────┤
│                     INTERACTIVE TIMELINE & SCENARIO BUILDER (SCRUBBER)                 │
│  [▶ Play] [⏸ Pause] [⏱ 00:00.00] ────────●──────────────────────────────────────────── │
│  Tracks: [Wind Gust] [Wave Slam] [IMU Drop] [GPS Loss] [Rudder Stall] [Safety Mode]    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Модульная структура фронтенда (`src/sia_sim/workbench/static/js/`):
- `state.js` — Реактивное хранилище состояния симуляции, пресетов и настроек.
- `playback.js` — 60 FPS движок плеера, интерполяция кадров, управление скоростью и непрерывное воспроизведение.
- `instruments.js` — Высокопроизводительный рендеринг 6 морских приборов на Canvas 2D (AWA/AWS, Heel, Pitch, Nav, Heave, Slam).
- `timeline.js` — Интерактивный таймлайн-скраббер и визуальный конструктор событий (порывы, волны, отказы датчиков).
- `query_loop.js` — Интерактивный диалог опроса шкипера (Active Sensing) с 2-колоночным селектором гардероба яхты и пересчетом рекомендаций СИА.
- `service_logger.js` — Служебный диагностический терминал логов (`SIA CORE`, `PHYSICS`, `SKIPPER`, `ORACLE`, `SIM_RUNNER`) с фильтрами, шторкой и экспортом JSON/CSV.
- `modals.js` — Модальные панели настройки параметров океана (`Custom Sea`) и параметров яхты (`Custom Vessel`).
- `app.js` — Точка входа, оркестрация компонентов верстака и сетевой обмен с `/api/run`.

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
│       └── rig.py      # Агрегатор SailRig, затенение, слот-эффект, 3D моменты, хуки
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

# Запуск тестов (238 passed)
uv run pytest
```

---

## 📜 Лицензия

Проект распространяется под лицензией MIT. Подробности см. в файле [LICENSE](LICENSE).
