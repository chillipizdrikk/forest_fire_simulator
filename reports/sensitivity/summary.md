# Forest fire experiments report

## Overall
- Total runs: 3000
- Mean burned area fraction (all / uncensored): 0.4209 / 0.4209
- Mean auc_normalized (all / uncensored): 0.0068 / 0.0068
- Mean time_to_extinguish (all / uncensored): 129.0037 / 129.0037
- Survival median time_to_extinguish (KM, right-censored by max_steps): 134.0000 (reached=True)
- Survival probability P(TTE > 200): 0.1837
- Critical share (all / uncensored): 0.2997 / 0.2997
- BAF quantiles p25/p50/p75/p95: 0.0151 / 0.3179 / 0.8832 / 0.9657
- Burned area p95/p99: 0.9657 / 0.9900
- Critical BAF threshold used: 0.8000
- Catastrophic probability (baf >= 0.8000): 0.2997
- Scenario ranking metric: auc_normalized_mean
- Censored runs (truncated by max_steps): 0 (0.0000)
- Pairwise significance tests: 398 / 435 significant pairs for baf; 408 / 435 for auc_normalized (BH q<=0.05).
- Note: censored runs can bias metrics: fire_duration and AUC are typically underestimated, while BAF-related risk can be understated when fire is still active at truncation.

## Worst scenarios by Mean auc_normalized (normalized)
- anchor_hot_dry: 0.0205
- transition_low_humidity_wind_strength_04: 0.0198
- anchor_mid_windy_rain_wind_strength_04: 0.0145

## Censoring max_steps bias audit
- Target rule: censored_share < 0.0200
- Initial max_steps: 500
- Final max_steps: 500
- Stop reason: target_met

## Absolute KPI ranking
### Mean burned area fraction (absolute, point estimate)
- anchor_hot_dry: 0.9880
- transition_low_humidity_wind_strength_04: 0.9553
- anchor_mid_windy_rain_wind_strength_04: 0.8782
### KPI comparison by scenario (all / uncensored)
- anchor_cool_wet: baf=0.0002/0.0002, auc_normalized=0.0001/0.0001, time_to_extinguish=3.8500/3.8500, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0001/0.0001/0.0003/0.0006
- anchor_hot_dry: baf=0.9880/0.9880, auc_normalized=0.0205/0.0205, time_to_extinguish=145.9800/145.9800, critical=1.0000/1.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.9874/0.9890/0.9905/0.9922
- anchor_mid_windy_rain: baf=0.2266/0.2266, auc_normalized=0.0041/0.0041, time_to_extinguish=125.3400/125.3400, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.1400/0.2141/0.3105/0.5017
- anchor_mid_windy_rain_humidity_025: baf=0.3697/0.3697, auc_normalized=0.0068/0.0068, time_to_extinguish=130.6000/130.6000, critical=0.0100/0.0100, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.2926/0.3636/0.4550/0.7727
- anchor_mid_windy_rain_humidity_035: baf=0.1874/0.1874, auc_normalized=0.0038/0.0038, time_to_extinguish=107.3500/107.3500, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.1095/0.1904/0.2607/0.3853
- anchor_mid_windy_rain_humidity_045: baf=0.0563/0.0563, auc_normalized=0.0014/0.0014, time_to_extinguish=68.6900/68.6900, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0011/0.0473/0.0843/0.1866
- anchor_mid_windy_rain_humidity_055: baf=0.0066/0.0066, auc_normalized=0.0004/0.0004, time_to_extinguish=22.8900/22.8900, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0002/0.0016/0.0076/0.0275
- anchor_mid_windy_rain_temperature_c_20: baf=0.1223/0.1223, auc_normalized=0.0024/0.0024, time_to_extinguish=94.2000/94.2000, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0035/0.1156/0.2097/0.3212
- anchor_mid_windy_rain_temperature_c_24: baf=0.1962/0.1962, auc_normalized=0.0037/0.0037, time_to_extinguish=110.6700/110.6700, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0026/0.2208/0.2900/0.4205
- anchor_mid_windy_rain_temperature_c_28: baf=0.2727/0.2727, auc_normalized=0.0051/0.0051, time_to_extinguish=116.7800/116.7800, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.1652/0.2739/0.3577/0.5803
- anchor_mid_windy_rain_wind_strength_04: baf=0.8782/0.8782, auc_normalized=0.0145/0.0145, time_to_extinguish=161.4800/161.4800, critical=0.9500/0.9500, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.9143/0.9267/0.9343/0.9405
- anchor_mid_windy_rain_wind_strength_06: baf=0.4702/0.4702, auc_normalized=0.0071/0.0071, time_to_extinguish=164.3300/164.3300, critical=0.1100/0.1100, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.3661/0.4707/0.6564/0.8222
- anchor_mid_windy_rain_wind_strength_08: baf=0.1537/0.1537, auc_normalized=0.0030/0.0030, time_to_extinguish=101.9800/101.9800, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0025/0.1530/0.2071/0.4306
- transition_cooler: baf=0.1882/0.1882, auc_normalized=0.0034/0.0034, time_to_extinguish=120.1500/120.1500, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0408/0.1863/0.2995/0.4243
- transition_high_humidity: baf=0.0169/0.0169, auc_normalized=0.0007/0.0007, time_to_extinguish=39.7300/39.7300, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0003/0.0061/0.0183/0.0860
- transition_low_humidity: baf=0.8362/0.8362, auc_normalized=0.0109/0.0109, time_to_extinguish=205.8100/205.8100, critical=0.8700/0.8700, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.8945/0.9195/0.9287/0.9395
- transition_low_humidity_humidity_025: baf=0.8374/0.8374, auc_normalized=0.0109/0.0109, time_to_extinguish=207.8100/207.8100, critical=0.9100/0.9100, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.8890/0.9139/0.9270/0.9401
- transition_low_humidity_humidity_035: baf=0.5376/0.5376, auc_normalized=0.0075/0.0075, time_to_extinguish=187.9600/187.9600, critical=0.1500/0.1500, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.3844/0.5568/0.7283/0.8325
- transition_low_humidity_humidity_045: baf=0.1446/0.1446, auc_normalized=0.0028/0.0028, time_to_extinguish=107.8000/107.8000, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0101/0.1426/0.2276/0.3688
- transition_low_humidity_humidity_055: baf=0.0135/0.0135, auc_normalized=0.0006/0.0006, time_to_extinguish=33.6000/33.6000, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0005/0.0030/0.0150/0.0610
- transition_low_humidity_temperature_c_20: baf=0.6958/0.6958, auc_normalized=0.0091/0.0091, time_to_extinguish=206.7400/206.7400, critical=0.5200/0.5200, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.6006/0.8155/0.8718/0.9059
- transition_low_humidity_temperature_c_24: baf=0.8054/0.8054, auc_normalized=0.0110/0.0110, time_to_extinguish=193.3500/193.3500, critical=0.8100/0.8100, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.8637/0.9076/0.9255/0.9353
- transition_low_humidity_temperature_c_28: baf=0.8746/0.8746, auc_normalized=0.0132/0.0132, time_to_extinguish=173.3100/173.3100, critical=0.9300/0.9300, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.9330/0.9451/0.9538/0.9585
- transition_low_humidity_wind_strength_04: baf=0.9553/0.9553, auc_normalized=0.0198/0.0198, time_to_extinguish=132.3000/132.3000, critical=0.9900/0.9900, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.9616/0.9657/0.9687/0.9729
- transition_low_humidity_wind_strength_06: baf=0.8202/0.8202, auc_normalized=0.0107/0.0107, time_to_extinguish=200.1400/200.1400, critical=0.8600/0.8600, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.8961/0.9131/0.9293/0.9405
- transition_low_humidity_wind_strength_08: baf=0.3124/0.3124, auc_normalized=0.0063/0.0063, time_to_extinguish=120.8900/120.8900, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.2618/0.3293/0.3869/0.5400
- transition_mid_humidity: baf=0.3005/0.3005, auc_normalized=0.0051/0.0051, time_to_extinguish=138.0700/138.0700, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.2166/0.3036/0.4036/0.6249
- transition_stronger_wind: baf=0.0800/0.0800, auc_normalized=0.0018/0.0018, time_to_extinguish=77.3900/77.3900, critical=0.0000/0.0000, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.0021/0.0573/0.1290/0.2321
- transition_warmer: baf=0.4733/0.4733, auc_normalized=0.0071/0.0071, time_to_extinguish=175.0800/175.0800, critical=0.0500/0.0500, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.3568/0.4654/0.6219/0.7997
- transition_weaker_wind: baf=0.8056/0.8056, auc_normalized=0.0110/0.0110, time_to_extinguish=195.8400/195.8400, critical=0.8300/0.8300, censored_share=0.0000, baf_q(p25/p50/p75/p95)=0.8478/0.8844/0.8967/0.9057
### Time-to-extinguish survival KPI (right-censored by max_steps)
- Interpret time via survival metrics (KM): median reflects extinction-time distribution robustly under censoring.
- Overall median TTE: 134.0000 (reached=True, lower_bound=490.0000)
- Overall P(TTE > 200): 0.1837
- Highest persistence scenarios by P(TTE > 200):
- transition_low_humidity_humidity_025: P(TTE>200)=0.5800, median=206.0000 (reached=True)
- transition_low_humidity: P(TTE>200)=0.5600, median=203.0000 (reached=True)
- transition_low_humidity_temperature_c_20: P(TTE>200)=0.5400, median=208.0000 (reached=True)
### Mean burned area fraction (95% bootstrap CI)
- anchor_hot_dry: 0.9880 (95% CI: 0.9871..0.9888)
- transition_low_humidity_wind_strength_04: 0.9553 (95% CI: 0.9355..0.9659)
- anchor_mid_windy_rain_wind_strength_04: 0.8782 (95% CI: 0.8328..0.9141)
### Conservative risk ranking (mean BAF upper 95% CI bound)
- anchor_hot_dry: upper_ci=0.9888 (mean=0.9880, 95% CI: 0.9871..0.9888)
- transition_low_humidity_wind_strength_04: upper_ci=0.9659 (mean=0.9553, 95% CI: 0.9355..0.9659)
- transition_low_humidity_temperature_c_28: upper_ci=0.9169 (mean=0.8746, 95% CI: 0.8251..0.9169)
### Mean AUC (absolute)
- anchor_hot_dry: 29867.4500
- transition_low_humidity_wind_strength_04: 26494.5500
- anchor_mid_windy_rain_wind_strength_04: 24369.4800

## Normalized KPI ranking
### Mean peak_fire_fraction (normalized)
- anchor_hot_dry: 0.0578
- transition_low_humidity_wind_strength_04: 0.0491
- anchor_mid_windy_rain_wind_strength_04: 0.0368

## Composite risk ranking
### Mean composite risk score (normalized, 95% bootstrap CI)
- anchor_hot_dry: 0.3403 (95% CI: 0.3392..0.3415)
- transition_low_humidity_humidity_025: 0.3252 (95% CI: 0.3057..0.3421)
- transition_low_humidity: 0.3242 (95% CI: 0.3039..0.3419)
### Mean auc_normalized (normalized)
- anchor_hot_dry: 0.0205
- transition_low_humidity_wind_strength_04: 0.0198
- anchor_mid_windy_rain_wind_strength_04: 0.0145

## Scenario pairwise significance tests
- Method: two-sided permutation test on mean differences (2000 resamples), Benjamini–Hochberg correction, and Cliff's delta effect size.
### baf
- anchor_cool_wet vs anchor_hot_dry: mean_diff=-0.9878, p=0.0005, q=0.0006, significant=True, cliffs_delta=-1.0000 (large)
- anchor_hot_dry vs anchor_mid_windy_rain: mean_diff=0.7614, p=0.0005, q=0.0006, significant=True, cliffs_delta=1.0000 (large)
- anchor_hot_dry vs anchor_mid_windy_rain_humidity_025: mean_diff=0.6183, p=0.0005, q=0.0006, significant=True, cliffs_delta=1.0000 (large)
- anchor_hot_dry vs anchor_mid_windy_rain_humidity_035: mean_diff=0.8006, p=0.0005, q=0.0006, significant=True, cliffs_delta=1.0000 (large)
- anchor_hot_dry vs anchor_mid_windy_rain_humidity_045: mean_diff=0.9317, p=0.0005, q=0.0006, significant=True, cliffs_delta=1.0000 (large)
### auc_normalized
- anchor_cool_wet vs anchor_hot_dry: mean_diff=-0.0204, p=0.0005, q=0.0006, significant=True, cliffs_delta=-1.0000 (large)
- anchor_hot_dry vs anchor_mid_windy_rain: mean_diff=0.0164, p=0.0005, q=0.0006, significant=True, cliffs_delta=1.0000 (large)
- anchor_hot_dry vs anchor_mid_windy_rain_humidity_025: mean_diff=0.0137, p=0.0005, q=0.0006, significant=True, cliffs_delta=1.0000 (large)
- anchor_hot_dry vs anchor_mid_windy_rain_humidity_035: mean_diff=0.0166, p=0.0005, q=0.0006, significant=True, cliffs_delta=1.0000 (large)
- anchor_hot_dry vs anchor_mid_windy_rain_humidity_045: mean_diff=0.0190, p=0.0005, q=0.0006, significant=True, cliffs_delta=1.0000 (large)

## continuous_param_correlations (uncontrolled)
- Note: these are global Pearson correlations for continuous params only.
- param_humidity vs peak_fire_size: r=-0.6800, 95% CI -0.6976..-0.6622, p=<1e-4, q=<1e-4, q<=0.05=True
- param_humidity vs max_spread_rate: r=-0.6511, 95% CI -0.6701..-0.6326, p=<1e-4, q=<1e-4, q<=0.05=True
- param_humidity vs baf: r=-0.6454, 95% CI -0.6628..-0.6275, p=<1e-4, q=<1e-4, q<=0.05=True
- param_humidity vs fire_duration: r=-0.4915, 95% CI -0.5169..-0.4670, p=<1e-4, q=<1e-4, q<=0.05=True
- param_humidity vs time_to_extinguish: r=-0.4915, 95% CI -0.5169..-0.4670, p=<1e-4, q=<1e-4, q<=0.05=True

## continuous_param_correlations (controlled by scenario)
- Method: within-scenario demeaning (scenario fixed-effects style).

## binary_param_effects
- For binary params: mean(True)-mean(False), plus point-biserial correlation with 95% CI.
- param_rain_enabled vs peak_fire_size: mean_diff=-413.3790, point_biserial_r=-0.4539, 95% CI -0.4891..-0.4167
- param_wind_enabled vs shape_complexity: mean_diff=-1.9100, point_biserial_r=-0.4040, 95% CI -0.4473..-0.3587
- param_rain_enabled vs max_spread_rate: mean_diff=-22.1693, point_biserial_r=-0.2878, 95% CI -0.3184..-0.2574
- param_rain_enabled vs baf: mean_diff=-0.5867, point_biserial_r=-0.2799, 95% CI -0.3054..-0.2534
- param_wind_enabled vs fire_duration: mean_diff=129.4693, point_biserial_r=0.2683, 95% CI 0.2415..0.2917

## Scenario-local top parameter-metric correlations
### anchor_cool_wet
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_hot_dry
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_humidity_025
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_humidity_035
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_humidity_045
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_humidity_055
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_temperature_c_20
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_temperature_c_24
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_temperature_c_28
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_wind_strength_04
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_wind_strength_06
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### anchor_mid_windy_rain_wind_strength_08
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_cooler
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_high_humidity
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_humidity_025
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_humidity_035
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_humidity_045
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_humidity_055
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_temperature_c_20
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_temperature_c_24
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_temperature_c_28
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_wind_strength_04
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_wind_strength_06
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_low_humidity_wind_strength_08
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_mid_humidity
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_stronger_wind
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_warmer
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...
### transition_weaker_wind
- Not enough information for per-scenario correlation estimation (runs: 100, minimum: 5, varying params: 0/9).
- ⚠️ Constant param_* in this scenario (9): param_conifer_ratio, param_f, param_height, param_humidity, param_init_tree_density...

## Family-level parameter sensitivity (OFAT-aware)
- Grouping rule: OFAT scenarios are grouped by axis `<base> / <varied_param>` (e.g. `transition_low_humidity / humidity`).
- Non-OFAT scenarios are excluded from this OFAT sensitivity section.
- For each OFAT axis: Pearson correlation and linear slope with 95% bootstrap CI.
### anchor_cool_wet
- Excluded: scenario name does not match OFAT naming convention.
### anchor_hot_dry
- Excluded: scenario name does not match OFAT naming convention.
### anchor_mid_windy_rain
- Excluded: scenario name does not match OFAT naming convention.
### anchor_mid_windy_rain / humidity
- param_humidity vs auc_normalized: r=-0.7470 (95% CI -0.7945..-0.6955), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-0.0215 (95% CI -0.0236..-0.0195)
- param_humidity vs baf: r=-0.7162 (95% CI -0.7584..-0.6726), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-1.2206 (95% CI -1.3546..-1.0932)
- param_humidity vs time_to_extinguish: r=-0.5693 (95% CI -0.6366..-0.5037), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-361.7900 (95% CI -412.5420..-309.2752)
### anchor_mid_windy_rain / temperature_c
- param_temperature_c vs auc_normalized: r=0.4026 (95% CI 0.2985..0.4964), p=<1e-4, q=<1e-4, q<=0.05=True, slope=0.0003 (95% CI 0.0002..0.0004)
- param_temperature_c vs baf: r=0.3676 (95% CI 0.2649..0.4607), p=<1e-4, q=<1e-4, q<=0.05=True, slope=0.0188 (95% CI 0.0131..0.0244)
- param_temperature_c vs time_to_extinguish: r=0.1269 (95% CI 0.0113..0.2414), p=0.0272, q=0.0272, q<=0.05=True, slope=2.8225 (95% CI 0.2523..5.2506)
### anchor_mid_windy_rain / wind_strength
- param_wind_strength vs auc_normalized: r=-0.8321 (95% CI -0.8830..-0.7754), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-0.0287 (95% CI -0.0308..-0.0266)
- param_wind_strength vs baf: r=-0.8290 (95% CI -0.8838..-0.7709), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-1.8111 (95% CI -1.9326..-1.6875)
- param_wind_strength vs time_to_extinguish: r=-0.3235 (95% CI -0.4189..-0.2315), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-148.7500 (95% CI -191.3692..-106.3654)
### transition_cooler
- Excluded: scenario name does not match OFAT naming convention.
### transition_high_humidity
- Excluded: scenario name does not match OFAT naming convention.
### transition_low_humidity
- Excluded: scenario name does not match OFAT naming convention.
### transition_low_humidity / humidity
- param_humidity vs baf: r=-0.8634 (95% CI -0.8974..-0.8228), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-2.8647 (95% CI -3.0140..-2.7011)
- param_humidity vs auc_normalized: r=-0.8374 (95% CI -0.8757..-0.7960), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-0.0354 (95% CI -0.0379..-0.0330)
- param_humidity vs time_to_extinguish: r=-0.6809 (95% CI -0.7356..-0.6266), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-602.7900 (95% CI -660.1089..-542.4097)
### transition_low_humidity / temperature_c
- param_temperature_c vs auc_normalized: r=0.4107 (95% CI 0.2936..0.5158), p=<1e-4, q=<1e-4, q<=0.05=True, slope=0.0005 (95% CI 0.0004..0.0006)
- param_temperature_c vs baf: r=0.2812 (95% CI 0.1638..0.3950), p=<1e-4, q=<1e-4, q<=0.05=True, slope=0.0223 (95% CI 0.0136..0.0307)
- param_temperature_c vs time_to_extinguish: r=-0.1814 (95% CI -0.2902..-0.0624), p=0.0015, q=0.0015, q<=0.05=True, slope=-4.1787 (95% CI -6.8435..-1.3530)
### transition_low_humidity / wind_strength
- param_wind_strength vs auc_normalized: r=-0.8571 (95% CI -0.8988..-0.8058), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-0.0338 (95% CI -0.0355..-0.0320)
- param_wind_strength vs baf: r=-0.7872 (95% CI -0.8359..-0.7277), p=<1e-4, q=<1e-4, q<=0.05=True, slope=-1.6075 (95% CI -1.7003..-1.5067)
- param_wind_strength vs time_to_extinguish: r=-0.0702 (95% CI -0.1501..0.0158), p=0.2246, q=0.2246, q<=0.05=False, slope=-28.5250 (95% CI -62.2458..6.5144)
### transition_mid_humidity
- Excluded: scenario name does not match OFAT naming convention.
### transition_stronger_wind
- Excluded: scenario name does not match OFAT naming convention.
### transition_warmer
- Excluded: scenario name does not match OFAT naming convention.
### transition_weaker_wind
- Excluded: scenario name does not match OFAT naming convention.

## Figures
- baf_hist: Global BAF histogram across all scenarios; dashed lines mark per-scenario means.
![baf_hist](figures/baf_hist.png)
- scenario_baf_boxplot: Per-scenario BAF boxplots for core scenarios only (median, IQR, outliers). OFAT variants are shown separately.
![scenario_baf_boxplot](figures/scenario_baf_boxplot.png)
- scenario_baf_boxplot_ofat: Separate BAF boxplots for OFAT subscenarios to avoid overcrowding.
![scenario_baf_boxplot_ofat](figures/scenario_baf_boxplot_ofat.png)
- scenario_baf_hist_grid: Small-multiple histograms with fixed BAF bins and per-panel y-scale: each panel shows one scenario distribution.
![scenario_baf_hist_grid](figures/scenario_baf_hist_grid.png)
- scenario_baf_mean_iqr: Scenario mean BAF with interquartile range as asymmetric error bars.
![scenario_baf_mean_iqr](figures/scenario_baf_mean_iqr.png)
- scenario_baf_mean_ofat_curves: OFAT sensitivity curves: mean BAF vs varied parameter value by base scenario.
![scenario_baf_mean_ofat_curves](figures/scenario_baf_mean_ofat_curves.png)
