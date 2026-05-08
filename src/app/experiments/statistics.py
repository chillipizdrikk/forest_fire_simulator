from __future__ import annotations

import math
from random import Random
from statistics import mean


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    q_clamped = _clamp_01(float(q))
    pos = (len(ordered) - 1) * q_clamped
    lower_idx = int(pos)
    upper_idx = min(lower_idx + 1, len(ordered) - 1)
    if lower_idx == upper_idx:
        return float(ordered[lower_idx])
    fraction = pos - lower_idx
    lower = ordered[lower_idx]
    upper = ordered[upper_idx]
    return float(lower + fraction * (upper - lower))


def _bootstrap_mean_ci(
    values: list[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int = 42,
) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        value = float(values[0])
        return value, value

    rng = Random(seed)
    n = len(values)
    sample_means = []
    for _ in range(n_resamples):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        sample_means.append(float(mean(sample)))

    alpha = (1.0 - confidence) / 2.0
    ci_low = _percentile(sample_means, alpha)
    ci_high = _percentile(sample_means, 1.0 - alpha)
    return ci_low, ci_high


def _pearson_corr(xs: list[float], ys: list[float]) -> float | None:
    if not xs or not ys or len(xs) != len(ys):
        return None
    x_mean = mean(xs)
    y_mean = mean(ys)
    x_std = (sum((x - x_mean) ** 2 for x in xs) / len(xs)) ** 0.5
    y_std = (sum((y - y_mean) ** 2 for y in ys) / len(ys)) ** 0.5
    if x_std == 0.0 or y_std == 0.0:
        return None
    cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / len(xs)
    return float(cov / (x_std * y_std))


def _pearson_p_value(xs: list[float], ys: list[float], corr: float) -> float:
    n = len(xs)
    if n != len(ys) or n < 3:
        return 1.0
    abs_corr = abs(float(corr))
    if abs_corr >= 1.0:
        return 0.0
    denom = 1.0 - (abs_corr**2)
    if denom <= 0.0:
        return 0.0
    t_stat = abs_corr * ((n - 2) / denom) ** 0.5
    # Normal approximation of two-sided p-value for Student's t.
    # Stable for ranking reliability, and avoids optional heavy dependencies.
    return float(_clamp_01(math.erfc(t_stat / math.sqrt(2.0))))


def _bootstrap_corr_ci(
    xs: list[float],
    ys: list[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    if not xs or not ys or len(xs) != len(ys):
        return 0.0, 0.0
    if len(xs) == 1:
        corr = _pearson_corr(xs, ys)
        if corr is None:
            return 0.0, 0.0
        return corr, corr

    rng = Random(seed)
    n = len(xs)
    sample_corrs: list[float] = []
    for _ in range(n_resamples):
        idxs = [rng.randrange(n) for _ in range(n)]
        bxs = [xs[i] for i in idxs]
        bys = [ys[i] for i in idxs]
        corr = _pearson_corr(bxs, bys)
        if corr is not None:
            sample_corrs.append(corr)

    if not sample_corrs:
        corr = _pearson_corr(xs, ys)
        if corr is None:
            return 0.0, 0.0
        return corr, corr

    alpha = (1.0 - confidence) / 2.0
    ci_low = _percentile(sample_corrs, alpha)
    ci_high = _percentile(sample_corrs, 1.0 - alpha)
    return ci_low, ci_high


def _linear_slope(xs: list[float], ys: list[float]) -> float | None:
    if not xs or not ys or len(xs) != len(ys):
        return None
    x_mean = mean(xs)
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom == 0.0:
        return None
    y_mean = mean(ys)
    numer = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    return float(numer / denom)


def _bootstrap_slope_ci(
    xs: list[float],
    ys: list[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 1000,
    seed: int = 42,
) -> tuple[float, float]:
    if not xs or not ys or len(xs) != len(ys):
        return 0.0, 0.0
    if len(xs) == 1:
        slope = _linear_slope(xs, ys)
        if slope is None:
            return 0.0, 0.0
        return slope, slope

    rng = Random(seed)
    n = len(xs)
    sample_slopes: list[float] = []
    for _ in range(n_resamples):
        idxs = [rng.randrange(n) for _ in range(n)]
        bxs = [xs[i] for i in idxs]
        bys = [ys[i] for i in idxs]
        slope = _linear_slope(bxs, bys)
        if slope is not None:
            sample_slopes.append(slope)

    if not sample_slopes:
        slope = _linear_slope(xs, ys)
        if slope is None:
            return 0.0, 0.0
        return slope, slope

    alpha = (1.0 - confidence) / 2.0
    ci_low = _percentile(sample_slopes, alpha)
    ci_high = _percentile(sample_slopes, 1.0 - alpha)
    return ci_low, ci_high


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _cliffs_delta(xs: list[float], ys: list[float]) -> float:
    if not xs or not ys:
        return 0.0
    greater = 0
    lower = 0
    for x in xs:
        for y in ys:
            if x > y:
                greater += 1
            elif x < y:
                lower += 1
    denom = len(xs) * len(ys)
    if denom == 0:
        return 0.0
    return float((greater - lower) / denom)


def _cliffs_delta_label(delta: float) -> str:
    ad = abs(float(delta))
    if ad < 0.147:
        return "negligible"
    if ad < 0.33:
        return "small"
    if ad < 0.474:
        return "medium"
    return "large"


def _permutation_test_mean_diff(
    xs: list[float],
    ys: list[float],
    *,
    n_resamples: int = 2000,
    seed: int = 42,
) -> float:
    if not xs or not ys:
        return 1.0
    observed = float(mean(xs) - mean(ys))
    combined = [*xs, *ys]
    n_x = len(xs)
    rng = Random(seed)
    extreme = 0
    for _ in range(max(1, int(n_resamples))):
        shuffled = list(combined)
        rng.shuffle(shuffled)
        perm_x = shuffled[:n_x]
        perm_y = shuffled[n_x:]
        perm_diff = float(mean(perm_x) - mean(perm_y))
        if abs(perm_diff) >= abs(observed):
            extreme += 1
    return float((extreme + 1) / (max(1, int(n_resamples)) + 1))


def _benjamini_hochberg(p_values: list[float]) -> list[float]:
    if not p_values:
        return []
    m = len(p_values)
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [1.0] * m
    running_min = 1.0
    for rank in range(m, 0, -1):
        idx, p = ordered[rank - 1]
        raw = float(p * m / rank)
        running_min = min(running_min, raw)
        adjusted[idx] = float(_clamp_01(running_min))
    return adjusted
