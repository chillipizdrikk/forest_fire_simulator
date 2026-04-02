# Forest fire experiments report

## Overall
- Total runs: 700
- Mean burned area fraction: 0.6222
- Burned area p95/p99: 0.9998 / 0.9999
- Critical BAF threshold used: 0.8000
- Catastrophic probability (baf >= 0.8000): 0.5729
- Scenario ranking metric: auc_normalized_mean
- Censored runs (truncated by max_steps): 3 (0.0043)
- Note: censored runs can bias metrics: fire_duration and AUC are typically underestimated, while BAF-related risk can be understated when fire is still active at truncation.

## Worst scenarios by Mean auc_normalized (normalized)
- baseline: 0.0343
- high_conifer: 0.0321
- extreme_dry_heat: 0.0208

## Absolute KPI ranking
### Mean burned area fraction (absolute, point estimate)
- high_conifer: 0.9995
- baseline: 0.9994
- extreme_dry_heat: 0.9935
### Mean burned area fraction (95% bootstrap CI)
- high_conifer: 0.9995 (95% CI: 0.9994..0.9996)
- baseline: 0.9994 (95% CI: 0.9994..0.9995)
- extreme_dry_heat: 0.9935 (95% CI: 0.9930..0.9939)
### Conservative risk ranking (mean BAF upper 95% CI bound)
- high_conifer: upper_ci=0.9996 (mean=0.9995, 95% CI: 0.9994..0.9996)
- baseline: upper_ci=0.9995 (mean=0.9994, 95% CI: 0.9994..0.9995)
- extreme_dry_heat: upper_ci=0.9939 (mean=0.9935, 95% CI: 0.9930..0.9939)
### Mean AUC (absolute)
- high_conifer: 30252.3500
- baseline: 30212.9000
- extreme_dry_heat: 30053.5500

## Normalized KPI ranking
### Mean peak_fire_fraction (normalized)
- baseline: 0.0769
- high_conifer: 0.0733
- extreme_dry_heat: 0.0575
### Mean auc_normalized (normalized)
- baseline: 0.0343
- high_conifer: 0.0321
- extreme_dry_heat: 0.0208

## Top parameter-metric correlations
- param_rain_intensity vs baf: -0.9787
- param_rain_enabled vs baf: -0.9512
- param_rain_intensity vs max_spread_rate: -0.9174
- param_temperature_c vs baf: 0.9083
- param_rain_intensity vs peak_fire_size: -0.9035

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
- baf_hist: Global BAF histogram across all scenarios; dashed lines mark per-scenario means.
![baf_hist](figures/baf_hist.png)
- scenario_baf_boxplot: Per-scenario BAF boxplots (median, IQR, outliers). Useful for ranking spread and stability.
![scenario_baf_boxplot](figures/scenario_baf_boxplot.png)
- scenario_baf_hist_grid: Small-multiple histograms with fixed BAF bins and per-panel y-scale: each panel shows one scenario distribution.
![scenario_baf_hist_grid](figures/scenario_baf_hist_grid.png)
- scenario_baf_mean_iqr: Scenario mean BAF with interquartile range as asymmetric error bars.
![scenario_baf_mean_iqr](figures/scenario_baf_mean_iqr.png)
