# Forest Fire Simulator

PySide6 desktop simulator for modeling forest fire spread with a cellular automata engine.

## Project structure

- `src/app/core/`
  - `constants.py` — cell-state constants.
  - `config.py` — simulation configuration dataclass.
  - `engine.py` — simulation engine (`ForestFireCA`).
  - `ca.py` — compatibility re-export layer.
- `src/app/ui/`
  - `main_window.py` — window layout/building.
  - `main_window_actions.py` — event handlers and user actions.
  - `main_window_state.py` — stats, UI state sync, and color mapping.
  - `panels/` — controls/statistics/legend panel builders.
- `src/app/experiments/`
  - `scenarios.py` — load `scenarios.yaml` definitions.
  - `runner.py` — batch runner and result persistence.
  - `analysis.py` — scenario comparison, sensitivity, correlations, and report generation.
- `src/app/main.py` — application entrypoint.
- `run_experiments.py` — CLI for multi-run experiments.

## Run UI

```bash
python -m src.app.main
```

## Run experiments (MVP)

```bash
python run_experiments.py --n 100 --seed 42
```

Outputs:

- Raw results: `results/raw/experiment_results_<timestamp>.csv`
- Optional parquet (if dependencies available): `results/raw/experiment_results_<timestamp>.parquet`
- Figures: `reports/figures/*.png`
- Auto-report: `reports/summary.md` and `reports/summary.html`

Result schema includes:

- `run_id`, `scenario`, `seed`
- `param_*` columns for simulation parameters
- Metrics per run (`baf`, `fire_duration`, `time_to_peak`, `auc`, `time_to_extinguish`, `max_spread_rate`, `critical`)

## Metrics dictionary

Єдиний контракт метрик описано в `src/app/core/metrics_schema.py`.

Core-метрики (рахуються у `src/app/core/metrics.py`):

- `baf` — burned area fraction, частка згорілих дерев (`0..1`), більше = гірше.
- `peak_fire_size` — пік одночасно палаючих клітин, більше = гірше.
- `time_to_peak` — крок до піку (0-based), трактування залежить від сценарію.
- `fire_duration` — тривалість активного горіння в кроках, більше = гірше.
- `auc` — інтегральна інтенсивність пожежі (`sum(burning_cells_t)`), більше = гірше.

Похідні метрики (для експериментів, також через `src/app/core/metrics.py` API):

- `time_to_extinguish` — крок повного згасання після старту пожежі.
- `max_spread_rate` — максимальний приріст `burning_cells_t` між сусідніми кроками.
- `steps_total` — фактична кількість виконаних кроків симуляції.
- `critical` — булева ознака `baf >= critical_baf_threshold`.

Приклад JSON payload:

```json
{
  "initial_tree_cells": 910,
  "burning_cells_t": [0, 1, 3, 7, 5, 0],
  "final_counts": {"burnt": 140, "burning": 0, "decid": 400, "conif": 370, "empty": 0, "barrier": 0},
  "metrics": {
    "baf": 0.1538,
    "peak_fire_size": 7,
    "time_to_peak": 3,
    "fire_duration": 4,
    "auc": 16
  }
}
```

Приклад рядка експериментів (`run_experiments.py`):

```text
run_id,scenario,seed,baf,peak_fire_size,time_to_peak,fire_duration,auc,time_to_extinguish,max_spread_rate,steps_total,critical
baseline-0000,baseline,123456,0.1538,7,3,4,16,5,4,6,false
```
