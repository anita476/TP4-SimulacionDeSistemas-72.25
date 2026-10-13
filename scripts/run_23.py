import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from paths import find_executable
from speed import bin_edges, fit_kbt, frame_speeds, mean_pdf, mean_v2, nearest_frame
from traj import Traj, read_traj

EXE = find_executable(ROOT, "TimeDrivenSimTable")
DT_FILE = ROOT / "docs" / "results" / "2.1" / "dt.txt"
FIGS = ROOT / "docs" / "results" / "2.3"
WORK = Path(os.environ.get("TEMP", "/tmp")) / "tp4_23_consigna"
OUT = WORK

N = 100
M = 0.025
V0 = 1.0
TF = 10.0
DT2 = 0.05
REPS = 10
SEEDS = list(range(1, REPS + 1))
BIN_WIDTH = 0.1
V_MAX = 2.5
TIMES = (0.0, 0.1, 0.5, 2.0, 10.0)


def save_stride(dt: float) -> int:
    return max(1, int(round(DT2 / dt)))


def read_dt() -> float:
    text = DT_FILE.read_text(encoding="utf-8").strip()
    dt = float(text)
    if not (dt > 0.0):
        raise RuntimeError(f"{DT_FILE}: dt must be > 0, got {dt}")
    return dt


def run_tp4(args: list[str]) -> None:
    cmd = [str(EXE), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(cmd)}\n{detail}")


def dump_path(seed: int) -> Path:
    return OUT / "dumps" / f"run_{seed}.txt"


def dump_complete(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        traj = read_traj(path)
    except (OSError, ValueError):
        return False
    return traj.N == N and traj.frames[-1].t + 1e-12 >= TF and not traj.obstacles


def simulate(seed: int, dt: float) -> Path:
    path = dump_path(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    if dump_complete(path):
        return path
    if path.exists():
        path.unlink()
    run_tp4(
        [
            "-N",
            str(N),
            "-m",
            f"{M:.10g}",
            "-v0",
            f"{V0:.10g}",
            "-seed",
            str(seed),
            "-dt",
            f"{dt:.10g}",
            "-tf",
            str(TF),
            "-n",
            str(save_stride(dt)),
            "--out",
            str(path),
        ]
    )
    return path


def write_pdf(path: Path, centers: list[float], means: list[float], stds: list[float]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("v f_mean f_std\n")
        for v, mean, std in zip(centers, means, stds):
            fh.write(f"{v:.10g} {mean:.8g} {std:.8g}\n")


def t_label(t: float) -> str:
    if abs(t) < 1e-12:
        return r"$t = 0$"
    return rf"$t = {t:g}\,\mathrm{{s}}$"


def mean_speed_at(trajs: list[Traj], t: float) -> float:
    speeds: list[float] = []
    for traj in trajs:
        speeds.extend(frame_speeds(nearest_frame(traj, t)))
    return sum(speeds) / len(speeds)


def snap_time(times: list[float], t: float) -> float:
    return min(times, key=lambda value: abs(value - t))


def plot_fv(
    output: Path,
    series: list[tuple[str, Path]],
    kbt: float | None = None,
    vline: tuple[float, str] | None = None,
) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "plotters" / "plot_fv.py"),
        "--output",
        str(output),
        "--xmax",
        f"{V_MAX:.10g}",
    ]
    for label, table in series:
        cmd += ["--series", label, str(table)]
    if kbt is not None:
        cmd += ["--fit", f"{kbt:.10g}", "--m", f"{M:.10g}"]
    if vline is not None:
        cmd += ["--vline", f"{vline[0]:.10g}", vline[1]]
    subprocess.check_call(cmd)


def main() -> None:
    if not DT_FILE.is_file():
        raise SystemExit(f"missing {DT_FILE}")
    dt = read_dt()
    print(f"dt={dt:g} from {DT_FILE}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)

    trajs: list[Traj] = []
    for seed in SEEDS:
        print(f"2.3 N={N} seed={seed} tf={TF} no obstacles", flush=True)
        path = simulate(seed, dt)
        traj = read_traj(path)
        if traj.m is None:
            raise RuntimeError(f"{path}: missing m")
        if abs(traj.m - M) > 1e-12:
            raise RuntimeError(f"{path}: m={traj.m}, expected {M}")
        if traj.obstacles:
            raise RuntimeError(f"{path}: expected no obstacles")
        trajs.append(traj)

    dump_times = sorted({frame.t for traj in trajs for frame in traj.frames})
    edges = bin_edges(V_MAX, BIN_WIDTH)
    chosen: list[float] = []
    for t in TIMES:
        snapped = snap_time(dump_times, t)
        if all(abs(snapped - prev) > 1e-12 for prev in chosen):
            chosen.append(snapped)

    series: list[tuple[str, Path]] = []
    tables: dict[float, Path] = {}
    for t in chosen:
        realizations = [frame_speeds(nearest_frame(traj, t)) for traj in trajs]
        centers, means, stds = mean_pdf(realizations, edges)
        tag = f"{t:.4g}".replace(".", "p")
        path = OUT / f"fv_t{tag}.txt"
        write_pdf(path, centers, means, stds)
        tables[t] = path
        series.append((t_label(t), path))
        print(f"  t={t:g}  <v>={mean_speed_at(trajs, t):.4g}", flush=True)

    t_fit = chosen[-1]
    stat_speeds: list[float] = []
    for traj in trajs:
        stat_speeds.extend(frame_speeds(nearest_frame(traj, t_fit)))
    centers, means, stds = mean_pdf(
        [frame_speeds(nearest_frame(traj, t_fit)) for traj in trajs],
        edges,
    )
    kbt_fit, sse = fit_kbt(M, centers, means)
    kbt_v0 = 0.5 * M * V0 * V0
    kbt_kin = 0.5 * M * mean_v2(stat_speeds)
    (OUT / "fit.txt").write_text(
        (
            f"t_fit {t_fit:.10g}\n"
            f"kBT_fit {kbt_fit:.8g}\n"
            f"kBT_mv02 {kbt_v0:.8g}\n"
            f"kBT_kinetic {kbt_kin:.8g}\n"
            f"sse {sse:.8g}\n"
            f"m {M:.8g}\n"
            f"v0 {V0:.8g}\n"
        ),
        encoding="utf-8",
    )
    print(
        f"kBT_fit={kbt_fit:.5g}  m v0^2/2={kbt_v0:.5g}  m <v^2>/2={kbt_kin:.5g}  sse={sse:.4g}",
        flush=True,
    )

    later = [(label, path) for t, (label, path) in zip(chosen, series) if t > 0.0]
    if not later:
        later = series
    plot_fv(OUT / "fv_tiempos.png", later, vline=(V0, t_label(0.0)))
    plot_fv(OUT / "fv_ajuste.png", [("simulación", tables[t_fit])], kbt=kbt_fit)

    FIGS.mkdir(parents=True, exist_ok=True)
    names = ["fv_tiempos.png", "fv_ajuste.png", "fit.txt"]
    names += [path.name for _t, path in series]
    for name in names:
        src = OUT / name
        if src.is_file():
            shutil.copy2(src, FIGS / name)
    print("done", FIGS, flush=True)


if __name__ == "__main__":
    main()
