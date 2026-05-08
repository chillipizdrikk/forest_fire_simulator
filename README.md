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

## Run virtual enviroment
```bash
.\venv\Scripts\activate
```

## Reproducibility

This project keeps the runtime dependencies in `requirements.txt`. The file hard-pins the direct dependencies used for reproducible CLI/report runs:

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

PowerShell equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the test suite:

```bash
python -m pytest
```

Run the main experiment batch with deterministic seeding:

```bash
python run_experiments.py \
  --scenarios scenarios.yaml \
  --n 100 \
  --seed 42 \
  --results-dir results/raw \
  --reports-dir reports
```

Fully reproduce the OFAT sensitivity report from `scenarios_sensitivity.yaml`:

```bash
python run_experiments.py \
  --scenarios scenarios_sensitivity.yaml \
  --n 100 \
  --seed 42 \
  --max-steps 500 \
  --critical-baf-threshold 0.8 \
  --censor-target-share 0.02 \
  --censor-max-retries 2 \
  --censor-step-multiplier 1.6 \
  --results-dir results/raw/sensitivity \
  --reports-dir reports/sensitivity
```

To capture the full transitive dependency tree for archival reproducibility after installation, generate a separate lock snapshot with:

```bash
python -m pip freeze > requirements-lock.txt
```

## Run UI

```bash
python -m src.app.main
```

## Run experiments (MVP)

```bash
python run_experiments.py --n 100 --seed 42
```

### Censoring bias audit (adaptive max_steps reruns)

CLI тепер підтримує автоматичний аудит цензурування:
- знаходить сценарії з `censored_share >= --censor-target-share`,
- перезапускає **лише ці** сценарії з більшим `max_steps`,
- порівнює метрики “до/після” у звіті,
- зупиняється, коли всі сценарії нижче цільового порогу або вичерпано `--censor-max-retries`.

Приклад:

```bash
python run_experiments.py \
  --n 100 \
  --max-steps 500 \
  --censor-target-share 0.02 \
  --censor-max-retries 2 \
  --censor-step-multiplier 1.6
```

PowerShell (multiline, використовуйте бектик `` ` `` замість `\`):

```powershell
python run_experiments.py `
  --n 100 `
  --max-steps 500 `
  --censor-target-share 0.02 `
  --censor-max-retries 2 `
  --censor-step-multiplier 1.6
```

Щоб вимкнути аудит:

```bash
python run_experiments.py --disable-censor-audit
```

### Recommended experiment patterns

- Keep the same `--n` across all comparisons (for fair scenario ranking):

```bash
python run_experiments.py --n 100 --seed 42
```

- Run several batch replicas with different seeds to validate ranking stability:

```bash
for s in 42 43 44 45 46; do
  python run_experiments.py --n 100 --seed "$s" \
    --results-dir "results/raw/seed_$s" \
    --reports-dir "reports/seed_$s"
done
```

- Для аналізу чутливості (перехідна зона + якорі) використовуйте `scenarios_sensitivity.yaml`:

> Увага: приклад нижче з `\` — для bash/zsh.  
> У PowerShell використовуйте один рядок або переноси через бектик `` ` ``.

```bash
python run_experiments.py \
  --scenarios scenarios_sensitivity.yaml \
  --n 100 \
  --seed 42 \
  --results-dir results/raw/sensitivity \
  --reports-dir reports/sensitivity
```

PowerShell (одним рядком):

```powershell
python run_experiments.py --scenarios scenarios_sensitivity.yaml --n 100 --seed 42 --results-dir results/raw/sensitivity --reports-dir reports/sensitivity
```

- Для global sensitivity (одночасна зміна 5 параметрів у перехідній зоні) використовуйте `scenarios_global_sensitivity.yaml`:

```bash
python run_experiments.py \
  --scenarios scenarios_global_sensitivity.yaml \
  --n 100 \
  --seed 42 \
  --results-dir results/raw/global_sensitivity \
  --reports-dir reports/global_sensitivity
```

PowerShell (одним рядком):

```powershell
python run_experiments.py --scenarios scenarios_global_sensitivity.yaml --n 100 --seed 42 --results-dir results/raw/global_sensitivity --reports-dir reports/global_sensitivity
```

У дипломній роботі розділяйте ці два типи sensitivity-аналізу:
- **OFAT sensitivity** (`scenarios_sensitivity.yaml`) — локальні тренди біля фіксованих базових сценаріїв, коли змінюється один фактор.
- **Global sensitivity** (`scenarios_global_sensitivity.yaml`) — загальний вплив параметрів за одночасної зміни `humidity`, `temperature_c`, `wind_strength`, `rain_intensity`, `conifer_ratio`, включно з 2D взаємодіями у звіті.

Outputs:

- Raw results: `results/raw/experiment_results_<timestamp>.csv`
- Optional parquet (if dependencies available): `results/raw/experiment_results_<timestamp>.parquet`
- Figures: `reports/figures/*.png`
- Auto-report: `reports/summary.md` and `reports/summary.html`

Для sensitivity-ранів у звіт також можуть додаватися 2D interaction heatmaps:
- `interaction_mean_baf_<param_x>_x_<param_y>.png`
- `interaction_catastrophic_<param_x>_x_<param_y>.png`

Result schema includes:

- `run_id`, `scenario`, `seed`
- `param_*` columns for simulation parameters
- Metrics per run (`baf`, `fire_duration`, `time_to_peak`, `auc`, `time_to_extinguish`, `max_spread_rate`, `critical`)

## Metrics dictionary

Контракт **run-level** метрик описано в `src/app/core/metrics_schema.py`.
Контракт **scenario/overall summary aggregates** описано в `src/app/core/summary_schema.py`.
Швидка шпаргалка українською: `docs/metrics_cheatsheet_uk.md`.
Український документ з qualitative / face validation припущень моделі та результатів зі звітів: `docs/model_validation_uk.md`.

Core-метрики (рахуються у `src/app/core/metrics.py`):

- `baf` — burned area fraction, частка згорілих дерев (`0..1`), більше = гірше.
- `peak_fire_size` — пік одночасно палаючих клітин, більше = гірше.
- `time_to_peak` — крок до піку (0-based), трактування залежить від сценарію.
- `fire_duration` — тривалість активного горіння в кроках, більше = гірше.
- `auc` — інтегральна інтенсивність пожежі (`sum(burning_cells_t)`), більше = гірше.

Похідні метрики (для експериментів, також через `src/app/core/metrics.py` API):

- `time_to_extinguish` — крок повного згасання після старту пожежі.
- `max_spread_rate` — `max(0, max приростів burning_cells_t між сусідніми кроками)`.
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

Приклад рядка run-level результатів (`run_experiments.py`, один прогін):

```text
run_id,scenario,seed,baf,peak_fire_size,time_to_peak,fire_duration,auc,time_to_extinguish,max_spread_rate,steps_total,critical
baseline-0000,baseline,123456,0.1538,7,3,4,16,5,4,6,false
```

Приклад scenario-level summary (агреговано по багатьох прогонах одного сценарію):

```json
{
  "scenario": "baseline",
  "runs": 100,
  "baf_mean_all": 0.4121,
  "baf_mean_uncensored": 0.3874,
  "baf_mean_ci_low": 0.3650,
  "baf_mean_ci_high": 0.4591,
  "critical_mean_all": 0.2700,
  "critical_mean_uncensored": 0.2200,
  "critical_share": 0.2700,
  "risk_score_mean": 0.5332,
  "risk_score_mean_uncensored": 0.5017,
  "risk_score_mean_ci_low": 0.4924,
  "risk_score_mean_ci_high": 0.5722
}
```
