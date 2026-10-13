import math

from metrics import mean_std
from traj import Frame, Traj

_INVPHI = 2.0 / (1.0 + 5.0 ** 0.5)


def frame_speeds(frame: Frame) -> list[float]:
    return [math.hypot(vx, vy) for _x, _y, vx, vy, _used in frame.particles]


def mean_v2(speeds: list[float]) -> float:
    if not speeds:
        raise ValueError("at least one speed is required")
    return sum(v * v for v in speeds) / len(speeds)


def nearest_frame(traj: Traj, t: float) -> Frame:
    if not traj.frames:
        raise ValueError("the trajectory has no frames")
    return min(traj.frames, key=lambda frame: abs(frame.t - t))


def bin_edges(vmax: float, width: float) -> list[float]:
    if not (vmax > 0.0) or not (width > 0.0):
        raise ValueError("vmax and bin width must be > 0")
    n = max(1, math.ceil(vmax / width))
    return [i * width for i in range(n + 1)]


def pdf_histogram(speeds: list[float], edges: list[float]) -> tuple[list[float], list[float]]:
    if len(edges) < 2:
        raise ValueError("need at least 2 bin edges")
    n = len(speeds)
    if n < 1:
        raise ValueError("at least one speed is required")
    counts = [0] * (len(edges) - 1)
    last = edges[-1]
    for v in speeds:
        if v < edges[0]:
            raise ValueError(f"speed {v} is below the first bin edge {edges[0]}")
        if v >= last:
            counts[-1] += 1
            continue
        placed = False
        for i in range(len(edges) - 1):
            if edges[i] <= v < edges[i + 1]:
                counts[i] += 1
                placed = True
                break
        if not placed:
            raise ValueError(f"speed {v} did not fall in any bin")
    centers: list[float] = []
    densities: list[float] = []
    for i, count in enumerate(counts):
        width = edges[i + 1] - edges[i]
        if not (width > 0.0):
            raise ValueError("bin edges must be strictly increasing")
        centers.append(0.5 * (edges[i] + edges[i + 1]))
        densities.append(count / (n * width))
    return centers, densities


def mean_pdf(realizations: list[list[float]], edges: list[float]) -> tuple[list[float], list[float], list[float]]:
    if not realizations:
        raise ValueError("at least one realization is required")
    columns: list[list[float]] = []
    centers: list[float] | None = None
    for speeds in realizations:
        mid, density = pdf_histogram(speeds, edges)
        if centers is None:
            centers = mid
        columns.append(density)
    assert centers is not None
    means: list[float] = []
    stds: list[float] = []
    for column in zip(*columns):
        mean, std = mean_std(list(column))
        means.append(mean)
        stds.append(std)
    return centers, means, stds


def mb_pdf(v: float, m: float, kbt: float) -> float:
    if not (m > 0.0):
        raise ValueError(f"m must be > 0, got {m}")
    if not (kbt > 0.0):
        raise ValueError(f"kBT must be > 0, got {kbt}")
    if v < 0.0:
        raise ValueError(f"v must be >= 0, got {v}")
    return (m * v / kbt) * math.exp(-m * v * v / (2.0 * kbt))


def fit_sse(kbt: float, m: float, centers: list[float], densities: list[float]) -> float:
    return sum((y - mb_pdf(x, m, kbt)) ** 2 for x, y in zip(centers, densities))


def fit_kbt(
    m: float,
    centers: list[float],
    densities: list[float],
    lo: float = 1.0e-6,
    hi: float = 1.0,
    tol: float = 1.0e-12,
) -> tuple[float, float]:
    if not (lo > 0.0 and lo < hi):
        raise ValueError("kBT bracket must satisfy 0 < lo < hi")
    if len(centers) != len(densities) or not centers:
        raise ValueError("centers and densities must be nonempty and aligned")

    def error(kbt: float) -> float:
        return fit_sse(kbt, m, centers, densities)

    a, b = lo, hi
    c = b - (b - a) * _INVPHI
    d = a + (b - a) * _INVPHI
    fc, fd = error(c), error(d)
    for _ in range(200):
        if abs(b - a) <= tol * (abs(a) + abs(b) + 1.0):
            break
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - (b - a) * _INVPHI
            fc = error(c)
        else:
            a, c, fc = c, d, fd
            d = a + (b - a) * _INVPHI
            fd = error(d)
    kbt = 0.5 * (a + b)
    return kbt, error(kbt)

def sweep_sse(
    m: float,
    centers: list[float],
    densities: list[float],
    kbt_values: list[float],
) -> list[tuple[float, float]]:
    """E(kBT) = sum (f_i - f_MB(v_i; kBT))^2 on a grid; the minimum must be interior (Teorica 0)."""
    if len(kbt_values) < 3:
        raise ValueError("need at least 3 kBT values to bracket a minimum")
    if kbt_values[0] <= 0.0 or any(b <= a for a, b in zip(kbt_values, kbt_values[1:])):
        raise ValueError("kBT values must be positive and strictly increasing")
    curve = [(kbt, fit_sse(kbt, m, centers, densities)) for kbt in kbt_values]
    i_min = min(range(len(curve)), key=lambda i: curve[i][1])
    if i_min == 0 or i_min == len(curve) - 1:
        raise ValueError(f"E(kBT) minimum is at the edge of the sweep (kBT = {curve[i_min][0]:g})")
    return curve