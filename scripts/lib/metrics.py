from math import fsum, isclose, isfinite
from pathlib import Path

from traj import Traj


def nu90(N: int) -> int:
    return -(-9 * N // 10)


def t_of_nu(series: list[tuple[float, int]], target: int) -> float | None:
    for t, nu in series:
        if nu >= target:
            return t
    return None


def nu_at(series: list[tuple[float, int]], t: float) -> int:
    """Nu of the last saved frame with time <= t (0 before the first frame)."""
    nu = 0
    for t_frame, nu_frame in series:
        if t_frame > t + 1e-9:
            break
        nu = nu_frame
    return nu


def t90_of_nu(N: int, series: list[tuple[float, int]]) -> float | None:
    return t_of_nu(series, nu90(N))


def t100_of_nu(N: int, series: list[tuple[float, int]]) -> float | None:
    return t_of_nu(series, N)


def t90_or_none(traj: Traj) -> float | None:
    return t90_of_nu(traj.N, [(frame.t, frame.nu) for frame in traj.frames])


def t90(traj: Traj) -> float:
    value = t90_or_none(traj)
    if value is None:
        last = traj.frames[-1]
        raise ValueError(f"Fu did not reach 0.9 (Fu={last.nu / traj.N:.3f} at t={last.t})")
    return value


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        raise ValueError("at least one value is required")
    mean = sum(values) / len(values)
    if len(values) == 1:
        return mean, 0.0
    var = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return mean, var ** 0.5


def _read_oscillator_series(path: str | Path, expected_fields: int) -> list[tuple[float, float]]:
    samples: list[tuple[float, float]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != expected_fields:
                raise ValueError(f"{path}:{lineno}: expected {expected_fields} fields, got {len(parts)}")
            try:
                t, x = float(parts[0]), float(parts[1])
            except ValueError:
                raise ValueError(f"{path}:{lineno}: expected numeric trajectory data") from None
            if not isfinite(t) or not isfinite(x):
                raise ValueError(f"{path}:{lineno}: time and position must be finite")
            samples.append((t, x))
    if not samples:
        raise ValueError(f"{path}: trajectory is empty")
    return samples


def trajectory_ecm(method_path: str | Path, analytic_path: str | Path) -> float:
    """Return mean squared position error for method (t, x_num, x_an) and analytic (t, x_an) files."""
    method = _read_oscillator_series(method_path, 3)
    analytic = _read_oscillator_series(analytic_path, 2)
    if len(method) != len(analytic):
        raise ValueError(f"trajectories have different sample counts: {len(method)} != {len(analytic)}")

    squared_errors: list[float] = []
    for index, ((method_t, method_x), (analytic_t, analytic_x)) in enumerate(zip(method, analytic)):
        if not isclose(method_t, analytic_t, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"trajectory times differ at sample {index}: {method_t} != {analytic_t}")
        squared_errors.append((method_x - analytic_x) ** 2)
    return fsum(squared_errors) / len(squared_errors)


def nu_series(traj: Traj) -> list[tuple[float, int]]:
    return [(frame.t, frame.nu) for frame in traj.frames]
