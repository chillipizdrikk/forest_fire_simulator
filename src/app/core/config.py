from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CAConfig:
    width: int = 200
    height: int = 200

    # Lightning as event.
    f: float = 0.01
    lightning_enabled: bool = True
    lightning_max_strikes_per_event: int = 1
    lightning_cooldown_steps: int = 20

    humidity: float = 0.0
    temperature_c: float = 25.0

    wind_enabled: bool = False
    wind_dir: str = "E"
    wind_strength: float = 0.6

    init_tree_density: float = 0.6
    seed: int | None = None

    conifer_ratio: float = 0.5
    flamm_decid: float = 0.85
    flamm_conif: float = 1.00

    burn_stage_factors: tuple[float, float, float] = (1.00, 0.55, 0.25)

    # Rain (manual)
    rain_enabled: bool = False
    rain_intensity: float = 0.0

    # Rain scenario (automatic)
    rain_scenario_enabled: bool = False
    rain_scenario_start_step: int = 20
    rain_scenario_end_step: int = 35
    rain_scenario_intensity: float = 0.5
