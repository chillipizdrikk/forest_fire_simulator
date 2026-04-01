# Forest fire experiments report

## Overall
- Total runs: 700
- Mean burned area fraction: 0.5572
- Burned area p95/p99: 0.9998 / 0.9999
- Critical BAF threshold used: 0.8000
- Catastrophic probability (baf >= 0.8000): 0.5557
- Scenario ranking metric: auc_normalized_mean
- Censored runs (truncated by max_steps): 9 (0.0129)
- Note: censored runs can bias metrics: fire_duration and AUC are typically underestimated, while BAF-related risk can be understated when fire is still active at truncation.

## Worst scenarios by Mean auc_normalized (normalized)
- baseline: 0.0343
- high_conifer: 0.0321
- dry_windy: 0.0190

## Absolute KPI ranking
### Mean burned area fraction (absolute, point estimate)
- high_conifer: 0.9995
- baseline: 0.9994
- dry_windy: 0.9875
### Mean burned area fraction (95% bootstrap CI)
- high_conifer: 0.9995 (95% CI: 0.9994..0.9996)
- baseline: 0.9994 (95% CI: 0.9994..0.9995)
- dry_windy: 0.9875 (95% CI: 0.9867..0.9882)
### Conservative risk ranking (mean BAF upper 95% CI bound)
- high_conifer: upper_ci=0.9996 (mean=0.9995, 95% CI: 0.9994..0.9996)
- baseline: upper_ci=0.9995 (mean=0.9994, 95% CI: 0.9994..0.9995)
- dry_windy: upper_ci=0.9882 (mean=0.9875, 95% CI: 0.9867..0.9882)
### Mean AUC (absolute)
- high_conifer: 30252.3500
- baseline: 30212.9000
- dry_windy: 29853.2600

## Normalized KPI ranking
### Mean peak_fire_fraction (normalized)
- baseline: 0.0769
- high_conifer: 0.0733
- dry_windy: 0.0534
### Mean auc_normalized (normalized)
- baseline: 0.0343
- high_conifer: 0.0321
- dry_windy: 0.0190

## Top parameter-metric correlations
- param_rain_enabled vs baf: -0.9916
- param_rain_intensity vs baf: -0.9450
- param_rain_enabled vs max_spread_rate: -0.9309
- param_rain_enabled vs peak_fire_size: -0.8937
- param_rain_intensity vs max_spread_rate: -0.8936

## Scenario-local top parameter-metric correlations
### baseline
- Not enough runs for per-scenario correlation estimation (minimum 5 runs).
### dry_windy
- Not enough runs for per-scenario correlation estimation (minimum 5 runs).
### extreme_dry_heat
- Not enough runs for per-scenario correlation estimation (minimum 5 runs).
### extreme_wet_cool
- Not enough runs for per-scenario correlation estimation (minimum 5 runs).
### high_conifer
- Not enough runs for per-scenario correlation estimation (minimum 5 runs).
### wet_cool
- Not enough runs for per-scenario correlation estimation (minimum 5 runs).
### windy_rain_burst
- Not enough runs for per-scenario correlation estimation (minimum 5 runs).

## Figures
![baf_hist](figures/baf_hist.png)
![scenario_baf_boxplot](figures/scenario_baf_boxplot.png)
