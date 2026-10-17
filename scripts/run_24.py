import os
import shutil
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from paths import find_executable
from metrics import mean_std, nu_at, t100_of_nu, t90_of_nu
from traj import read_nu_series

EXE = find_executable(ROOT, "TimeDrivenSimTable")
DT_FILE = ROOT / "docs" / "results" / "2.1" / "dt.txt"
FIGS = ROOT / "docs" / "results" / "2.4"
WORK = Path(os.environ.get("TEMP", "/tmp")) / "tp4_24_event"
OUT = WORK

R = 0.51
r = 0.0175
XO = r
TF = 2000.0
T_REF = 30.0  # the tf of 2.1.b: Fu(T_REF) is what the 2.1.b outputs give literally
DT2 = 0.05
REPS = 10
SEEDS = list(range(1, REPS + 1))
N_RUNTIME = (10, 20, 30, 50, 100, 200, 300, 400, 500, 650)


def packing_phi(n: int) -> float:
    return n * (r / R) ** 2


def tp4_init(n: int) -> str:
    return "hex" if n > 400 else "random"


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


def dump_dir(n: int) -> Path:
    return OUT / "dumps" / f"N{n}"


def dump_complete(path: Path, n: int) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        N, series = read_nu_series(path)
    except (OSError, ValueError):
        return False
    return N == n and (series[-1][1] >= n or series[-1][0] + 1e-9 >= TF)


def simulate(n: int, seed: int, dt: float) -> Path:
    folder = dump_dir(n)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"run_{seed}.txt"
    if dump_complete(path, n):
        return path
    if path.exists():
        path.unlink()
    run_tp4(
        [
            "-N",
            str(n),
            "-seed",
            str(seed),
            "-xo",
            f"{XO:.10g}",
            "-init",
            tp4_init(n),
            "-dt",
            f"{dt:.10g}",
            "-tf",
            str(TF),
            "--until-used",
            "-n",
            str(save_stride(dt)),
            "--out",
            str(path),
        ]
    )
    N, series = read_nu_series(path)
    if N != n:
        raise RuntimeError(f"{path}: N={N}, expected {n}")
    if series[-1][1] < n:
        print(f"  seed={seed}: Nu={series[-1][1]}/{n} at tf={TF:g} s (incomplete, reported as Fu(tf))", flush=True)
    return path


def stats(values: list[float]) -> tuple[float, float]:
    return mean_std(values) if values else (float("nan"), float("nan"))


def summarize(n: int) -> dict[str, float | int]:
    t90s: list[float] = []
    t100s: list[float] = []
    fu_end: list[float] = []
    fu_ref: list[float] = []
    for seed in SEEDS:
        path = dump_dir(n) / f"run_{seed}.txt"
        N, series = read_nu_series(path)
        if N != n:
            raise RuntimeError(f"{path}: N={N}, expected {n}")
        fu_end.append(series[-1][1] / n)
        fu_ref.append(nu_at(series, T_REF) / n)
        t90 = t90_of_nu(n, series)
        t100 = t100_of_nu(n, series)
        if t90 is not None:
            t90s.append(t90)
        if t100 is not None:
            t100s.append(t100)
    t90_mean, t90_std = stats(t90s)
    t100_mean, t100_std = stats(t100s)
    fu_mean, fu_std = mean_std(fu_end)
    fu30_mean, fu30_std = mean_std(fu_ref)
    return {
        "N": n,
        "phi": packing_phi(n),
        "n_t90": len(t90s),
        "n_t100": len(t100s),
        "fu_tmax_mean": fu_mean,
        "fu_tmax_std": fu_std,
        "fu30_mean": fu30_mean,
        "fu30_std": fu30_std,
        "t90_mean": t90_mean,
        "t90_std": t90_std,
        "t100_mean": t100_mean,
        "t100_std": t100_std,
    }


def write_observable(path: Path, rows: list[dict[str, float | int]], mean_key: str, std_key: str) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("N phi t_mean t_std\n")
        for row in rows:
            fh.write(f"{row['N']} {row['phi']:.10g} {row[mean_key]:.8g} {row[std_key]:.8g}\n")


def write_report(path: Path, rows: list[dict[str, float | int]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("N phi n_t90 t90_mean t90_std n_t100 t100_mean t100_std fu_tmax_mean fu_tmax_std fu30_mean fu30_std\n")
        for row in rows:
            fh.write(
                f"{row['N']} {row['phi']:.10g} {row['n_t90']} {row['t90_mean']:.8g} {row['t90_std']:.8g} "
                f"{row['n_t100']} {row['t100_mean']:.8g} {row['t100_std']:.8g} "
                f"{row['fu_tmax_mean']:.8g} {row['fu_tmax_std']:.8g} "
                f"{row['fu30_mean']:.8g} {row['fu30_std']:.8g}\n"
            )


def table_has_rows(path: Path) -> bool:
    return data_rows(path) > 0


def data_rows(path: Path) -> int:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    return max(0, len(lines) - 1)


def plot_series(
    output: Path,
    series: list[tuple[str, Path]],
    xlabel: str,
    ylabel: str,
    ymax: float | None = None,
    logy: bool = False,
    logx: bool = False,
) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "plotters" / "plot_density.py"),
        "--output",
        str(output),
        "--xlabel",
        xlabel,
        "--ylabel",
        ylabel,
    ]
    if ymax is not None:
        cmd += ["--ymax", f"{ymax:.10g}"]
    if logy:
        cmd += ["--logy"]
    if logx:
        cmd += ["--logx"]
    for label, path in series:
        if table_has_rows(path):
            cmd += ["--series", label, str(path)]
    if "--series" not in cmd:
        raise RuntimeError(f"no data series for {output}")
    subprocess.check_call(cmd)


def main() -> None:
    if not DT_FILE.is_file():
        raise SystemExit(f"missing {DT_FILE}")
    dt = read_dt()
    print(f"dt={dt:g} from {DT_FILE}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | int]] = []
    for n in N_RUNTIME:
        init = tp4_init(n)
        for seed in SEEDS:
            print(f"2.4 N={n} seed={seed} init={init} xo=r until Nu=N", flush=True)
            simulate(n, seed, dt)
        row = summarize(n)
        rows.append(row)
        print(
            f"  phi={row['phi']:.4g}  <t90>={row['t90_mean']:.3f}s ({row['n_t90']}/{REPS})  "
            f"<t100>={row['t100_mean']:.3f}s ({row['n_t100']}/{REPS})  Fu(tf)={row['fu_tmax_mean']:.3f}",
            flush=True,
        )

    t90_path = OUT / "t90_vs_phi.txt"
    t100_path = OUT / "t100_vs_phi.txt"
    write_observable(t90_path, rows, "t90_mean", "t90_std")
    write_observable(t100_path, rows, "t100_mean", "t100_std")
    write_report(OUT / "report.txt", rows)

    # Literal reading of 2.4.a: what the 2.1.b horizon (tf = 30 s) gives.
    fu30_path = OUT / "fu30_vs_phi.txt"
    write_observable(fu30_path, rows, "fu30_mean", "fu30_std")  # columns N phi t_mean t_std: plot_density reads them as is
    plot_series(
        OUT / "fu30_vs_phi.png",
        [(rf"$F_u(t = {T_REF:g}\,\mathrm{{s}})$", fu30_path)],
        r"densidad $\phi$",
        rf"fracción usada a $t = {T_REF:g}$ s",
        ymax=1.05,
    )

    time_series: list[tuple[str, Path]] = []
    if data_rows(t90_path) >= 2:
        time_series.append((r"$t_{90}$", t90_path))
    if data_rows(t100_path) >= 2:
        time_series.append((r"$t_{100}$", t100_path))
    t90_plot = OUT / "t90_t100_vs_phi.png"
    t90_plot_linear = OUT / "t90_t100_vs_phi_lineal.png"
    if time_series:
        plot_series(t90_plot, time_series, r"densidad $\phi$", "tiempo (s)", logy=True, logx=True)
        plot_series(t90_plot_linear, time_series, r"densidad $\phi$", "tiempo (s)")
    else:
        for path in (t90_plot, t90_plot_linear):
            if path.is_file():
                path.unlink()
    FIGS.mkdir(parents=True, exist_ok=True)
    for name in (
        "t90_t100_vs_phi.png",
        "t90_t100_vs_phi_lineal.png",
        "t90_vs_phi.txt",
        "t100_vs_phi.txt",
        "fu30_vs_phi.txt",
        "fu30_vs_phi.png",
        "report.txt",
    ):
        src = OUT / name
        dest = FIGS / name
        if src.is_file():
            shutil.copy2(src, dest)
        elif dest.is_file():
            dest.unlink()
    print("done", FIGS, flush=True)


if __name__ == "__main__":
    main()
