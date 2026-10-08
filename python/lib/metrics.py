from traj import Traj


def nu90(n: int) -> int:
    return -(-9 * n // 10)


def t90_or_none(traj: Traj) -> float | None:
    target = nu90(traj.n)
    for frame in traj.frames:
        if frame.nu >= target:
            return frame.t
    return None


def t90(traj: Traj) -> float:
    value = t90_or_none(traj)
    if value is None:
        last = traj.frames[-1]
        raise ValueError(f"Fu did not reach 0.9 (Fu={last.nu / traj.n:.3f} at t={last.t})")
    return value


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        raise ValueError("at least one value is required")
    mean = sum(values) / len(values)
    if len(values) == 1:
        return mean, 0.0
    var = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return mean, var ** 0.5


def nu_series(traj: Traj) -> list[tuple[float, int]]:
    return [(frame.t, frame.nu) for frame in traj.frames]
