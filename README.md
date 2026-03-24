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
- `src/app/main.py` — application entrypoint.

## Run

```bash
python -m src.app.main
```
