# 🌊 SIA Simulation (`sia-sim`)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Package Manager: uv](https://img.shields.io/badge/uv-fast%20python-purple.svg?logo=astral&logoColor=white)](https://astral.sh/uv)
[![Tests: 204 passed](https://img.shields.io/badge/tests-204%20passed-brightgreen.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Architecture: Hard Boundary](https://img.shields.io/badge/boundary-strict%20SensorFrame-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**SIA Simulation** — детерминированный физико-сенсорный испытательный стенд (100 Гц) для верификации ядра **Safety & Intelligence Architecture (SIA) Core**. 

Платформа моделирует динамику парусного судна, гидрометеорологическую обстановку и генерирует синтетический поток наблюдений (`SensorFrame`), тестируя алгоритмы предиктивной безопасности SIA в экстремальных морских условиях (включая сценарий брочинга **SIM-005**) с независимой оценкой через модуль **Oracle**.

---

## 🎯 Ключевые архитектурные принципы

```
  ┌─────────────────────────────────────────────────────────────┐
  │                 SIA SIMULATION RUNNER                       │
  │                                                             │
  │   ┌─────────────────────┐       ┌───────────────────────┐   │
  │   │  World Environment  │  ───▶ │ 4-DOF Vessel Dynamics │   │
  │   │   (Wind/Waves/Sea)  │       │  (Surge/Sway/Yaw/Roll)│   │
  │   └─────────────────────┘       └───────────────────────┘   │
  │              │                              │               │
  │              ▼                              ▼               │
  │        ┌──────────────────────────────────────────┐         │
  │        │   GroundTruthFrame (Physical Reality)    │         │
  │        └──────────────────────────────────────────┘         │
  │              │                               │              │
  │              ▼                               ▼              │
  │   ┌───────────────────────┐      ┌───────────────────────┐  │
  │   │    Sensor Pipeline    │      │    Oracle Engine      │  │
  │   │ (IMU/GPS/Wind/Faults) │      │ (Independent Safety)  │  │
  │   └───────────────────────┘      └───────────────────────┘  │
  └──────────────┼───────────────────────────────┼──────────────┘
                 │ SensorFrame ONLY              │
                 │ (Hard Boundary: INV-01/02)    │
                 ▼                               ▼
  ┌───────────────────────────────┐  ┌──────────────────────────┐
  │           SIA CORE            │  │        EVALUATOR         │
  │  Predictive Risk & Advisories │─▶│   Score & Verification   │
  │  (Candidate Responses)        │  │     (PASS / FAIL)        │
  └───────────────────────────────┘  └──────────────────────────┘
```

1. **Строгая граница данных (Hard Boundary)**: 
   - `SensorFrame` — **единственная** структура данных, поступающая в SIA Core.
   - `GroundTruthFrame`, параметры физики и внутреннее состояние мира **никогда не утекают** в SIA Core (`INV-01`, `INV-02`).
2. **100% Детерминизм (Bit-for-Bit Reproducibility)**:
   - Шаг симуляции фиксирован на 10 мс (100 Гц).
   - Нулевая зависимость от системного времени (Wall Clock).
   - Детерминированные PRNG-потоки для каждого датчика и канала помех.
3. **Единый источник истины конфигурации судна (Single Source of Truth)**:
   - Геометрия, водоизмещение, поляры и парусное вооружение яхты определены в каноническом объекте `DEFAULT_VESSEL_CONFIG`.
   - Пресеты мира управляют только условиями окружающей среды.

---

## ⚡ Быстрый старт

### Требования
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (рекомендуемый ультрабыстрый пакетный менеджер)

### 1. Установка зависимостей
```bash
# Клонирование репозитория
git clone https://github.com/dzentec/SIA_SIM.git
cd SIA_SIM

# Синхронизация виртуального окружения
uv sync
```

### 2. Запуск интерактивного Веб-Верстака (Workbench)
```bash
uv run sia-sim --workbench --port 8080
```
После запуска откройте в браузере: **`http://localhost:8080`**

### 3. Запуск верификации сценария в CLI
```bash
# Запуск золотого сценария SIM-005 (Broach Precursor)
uv run sia-sim --scenario SIM-005

# Запуск с указанием сида и длительности
uv run sia-sim --scenario SIM-005 --seed 42 --duration 20
```

### 4. Запуск тестов
```bash
uv run pytest
```

---

## 🧭 Пресеты морского мира (World Presets)

В симуляторе реализованы 4 реалистичных фоновых состояния океана с непрерывным шумом волн и ветра:

| Пресет | Ветер (TWS) | Волна ($H_s$) | Период ($T_p$) | Динамика судна |
| :--- | :--- | :--- | :--- | :--- |
| **`harbour`** | 4.0 kt | 0.2 m | 3.0 s | Спокойная гавань, легкая рябь, плавный ход |
| **`cruise`** | 13.0 kt | 1.0 m | 4.5 s | Умеренный галфвинд, крен ~12°, стабильный ход 5.8 kt |
| **`fresh`** | 21.0 kt | 2.1 m | 5.0 s | Свежий бриз, крутая волна, выраженная бортовая и килевая качка |
| **`gale`** | 28.0 kt | 3.2 m | 6.5 s | Штормовое море, высокий риск брочинга, срыв руля |

> **Примечание**: Пресеты задают чистое окружение. Любые сценарии и аномалии (шквалы, гидроудары, отказы датчиков) расставляются пользователем на интерактивном таймлайне.

---

## 🎛 Интерактивный веб-кокпит (Workbench)

Интерфейс спроектирован в стиле темного навигационного терминала высокого разрешения (Glassmorphism Dark Theme):

* 🌊 **World Preset & Settings**: Быстрый выбор погодных условий, настройка длительности (5–120 с) и генератора шума.
* 🔬 **Ground Truth Physics Lab**: Терминал истинных гидродинамических параметров (TWS, TWD, истинный крен, дифферент, вертикальная перегрузка, слеминг, срыв руля).
* 💡 **Skipper Interactive Query Loop**: Диалоговый интерфейс взаимодействия капитана с ядром SIA Core для уточнения парусного плана и подтверждения трима.
* 🧭 **6 Analog Marine Canvas Dials**:
  1. *Apparent Wind Angle & Speed (AWA / AWS)*
  2. *Heel / Inclinometer (Roll angle & dynamic limit)*
  3. *Pitch Angle (Trim / Heave encounter)*
  4. *Compass Navigation & Heading (COG / SOG)*
  5. *Heave Displacement Monitor (Wave motion)*
  6. *Hull Slamming Impact G-Force Dial*
* ⏱ **Interactive Timeline & Scenario Builder**:
  - Посекундная полоса времени со скруббером.
  - Добавление и удаление событий: `Wind Gust`, `Wave Impact / Slam`, `IMU Dropout`, `GPS Fix Loss`, `Rudder Stall`.
  - Управление воспроизведением (Play, Pause, Step-by-step, Replay).
* 🛡 **SIA Core Decision & Advisory Stream**:
  - Индикаторы риска брочинга (Broach Risk Matrix).
  - Рекомендации экипажу (`Ease Sheet`, `Bear Away`, `Reef Main`).
  - Вердикт Oracle: **`PASS / FAIL`** с оценкой задержки реакции (Response Latency $< 250$ ms).

---

## 📁 Структура проекта

```
src/sia_sim/
├── contracts/          # Pydantic v2 схемы данных (SensorFrame, GroundTruth, Scenario)
│   ├── data.py         # Сенсорные и физические структуры данных
│   ├── evaluation.py   # Контракты для Oracle и Evaluator
│   └── scenario.py     # Спецификация сценария и VesselConfig
├── core/               # Ядро симулятора
│   ├── clock.py        # Дискретные 100 Гц часы (SimulationClock)
│   └── rng.py          # Изолированные детерминированные потоки PRNG
├── physics/            # Физический движок
│   ├── dynamics.py     # 4-DOF гидродинамика и дифференциальные уравнения движения
│   ├── environment.py  # Моделирование ветра, волн и течений
│   ├── forces.py       # Аэродинамика парусов, гидродинамика руля, восстанавливающий момент
│   └── integrator.py   # Численное интегрирование Рунге-Кутты 4-го порядка (RK4)
├── sensors/            # Сенсорный пайплайн и модели отказов
│   ├── channels.py     # Шумы, смещения (bias), дрейф, квантование, задержка
│   └── pipeline.py     # Генерация 100 Гц SensorFrame
├── scenarios/          # Каталог пресетов и золотых сценариев
│   ├── presets.py      # Реалистичные пресеты морского мира (World Presets)
│   └── sim005.py       # Канонический сценарий SIM-005 (Broach Precursor)
├── sia/                # Mock и протоколы интеграции с SIA Core
│   └── mock_sia.py     # Эталонная реализация ядра безопасности
├── evaluation/         # Модуль независимой верификации
│   ├── oracle.py       # Независимый расчет истинного риска по Ground Truth
│   └── evaluator.py    # Сравнение решений SIA Core с требованиями безопасности
└── workbench/          # Веб-сервер и интерфейс кокпита
    ├── server.py       # FastAPI + WebSocket стриминг 100 Гц
    └── static/         # HTML5 / Canvas / Vanilla CSS веб-верстак
```

---

## 🧪 Качество и тестирование

Система покрыта строгим набором из 204 юнит- и интеграционных тестов:
- `test_sia_boundary.py`: AST-анализ на отсутствие запрещенных импортов `GroundTruthFrame` в пакете `sia`.
- `test_physics_determinism.py`: Побитовая воспроизводимость траекторий при одинаковых сидах.
- `test_sensor_determinism.py`: Статистическая проверка распределений шумов и изоляции потоков PRNG.
- `test_simulation_runner.py`: Проверка прохождения сценариев SIM-005 и BENIGN.
- `test_world_presets.py`: Верификация чистого морского фона и корректности параметров.

Запуск проверки:
```bash
# Запуск линтера
uv run ruff check src/ tests/

# Запуск тестов
uv run pytest -v
```

---

## 📜 Лицензия

Проект распространяется под лицензией MIT. Подробности см. в файле [LICENSE](LICENSE).
