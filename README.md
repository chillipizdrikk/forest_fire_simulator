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
