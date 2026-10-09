import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "lib"))

from metrics import mean_std, t90_of_nu
from traj import read_nu_series

EXE = ROOT / "build-local" / "TimeDrivenSim.exe"
DT_FILE = ROOT / "docs" / "results" / "2.1" / "dt.txt"
FIGS = ROOT / "docs" / "results" / "2.2"
WORK = Path(os.environ.get("TEMP", "/tmp")) / "tp4_22_consigna"
OUT = WORK

R = 0.51
r = 0.0175
XO_MIN = r
XO_MAX = R - r
N_XO = 9
N_MAIN = 100
N_LOW = 20
TMAX = 100.0
DT2 = 0.05
REPS = 5
SEEDS = list(range(1, REPS + 1))


def xo_values() -> list[float]:
    span = XO_MAX - XO_MIN
    return [XO_MIN + i * span / (N_XO - 1) for i in range(N_XO)]


def xo_tag(xo: float) -> str:
    return f"{xo:.6f}"


def xo_label(xo: float) -> str:
    if abs(xo - XO_MIN) < 1e-12:
        return r"$x_o = r$"
    if abs(xo - XO_MAX) < 1e-12:
        return r"$x_o = R - r$"
    return rf"$x_o = {xo:.3g}\,\mathrm{{m}}$"


def dump_dir(n: int, xo: float) -> Path:
    return OUT / "dumps" / f"N{n}" / f"xo{xo_tag(xo)}"


def save_stride(dt: float) -> int:
    return max(1, int(round(DT2 / dt)))


def run_tp4(args: list[str]) -> None:
    cmd = [str(EXE), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(cmd)}\n{detail}")


def read_dt() -> float:
    text = DT_FILE.read_text(encoding="utf-8").strip()
    dt = float(text)
    if not (dt > 0.0):
        raise RuntimeError(f"{DT_FILE}: dt must be > 0, got {dt}")
    return dt


def dump_complete(path: Path, n: int) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        N, series = read_nu_series(path)
    except (OSError, ValueError):
        return False
    return N == n and series[-1][0] + 1e-12 >= TMAX


def simulate(n: int, xo: float, seed: int, dt: float) -> Path:
    folder = dump_dir(n, xo)
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
            f"{xo:.10g}",
            "-dt",
            f"{dt:.10g}",
            "-tf",
            str(TMAX),
            "-n",
            str(save_stride(dt)),
            "--out",
            str(path),
        ]
    )
    return path


def summarize_folder(n: int, xo: float) -> tuple[dict[str, float | int | None], list[tuple[int, float, float]]]:
    folder = dump_dir(n, xo)
    t90s: list[float] = []
    fu_end: list[float] = []
    missed: list[tuple[int, float, float]] = []
    for seed in SEEDS:
        path = folder / f"run_{seed}.txt"
        N, series = read_nu_series(path)
        if N != n:
            raise RuntimeError(f"{path}: N={N}, expected {n}")
        t_last, nu_last = series[-1]
        fu = nu_last / n
        fu_end.append(fu)
        t90 = t90_of_nu(n, series)
        if t90 is None:
            missed.append((seed, fu, t_last))
        else:
            t90s.append(t90)
    fu_mean, fu_std = mean_std(fu_end)
    row: dict[str, float | int | None] = {
        "xo": xo,
        "n_reached": len(t90s),
        "fu_tmax_mean": fu_mean,
        "fu_tmax_std": fu_std,
        "t90_mean": None,
        "t90_std": None,
    }
    if len(t90s) == REPS:
        mean, std = mean_std(t90s)
        row["t90_mean"] = mean
        row["t90_std"] = std
    return row, missed


def write_tables(n: int, rows: list[dict[str, float | int | None]]) -> Path:
    plot_path = OUT / f"t90_N{n}.txt"
    report_path = OUT / f"report_N{n}.txt"
    with plot_path.open("w", encoding="utf-8") as fh:
        fh.write("xo t90_mean t90_std\n")
        for row in rows:
            if row["t90_mean"] is None:
                continue
            fh.write(f"{row['xo']:.10g} {row['t90_mean']:.8g} {row['t90_std']:.8g}\n")
    with report_path.open("w", encoding="utf-8") as fh:
        fh.write("xo n_reached t90_mean t90_std fu_tmax_mean fu_tmax_std\n")
        for row in rows:
            t90_mean = "nan" if row["t90_mean"] is None else f"{row['t90_mean']:.8g}"
            t90_std = "nan" if row["t90_std"] is None else f"{row['t90_std']:.8g}"
            fh.write(
                f"{row['xo']:.10g} {row['n_reached']} {t90_mean} {t90_std} "
                f"{row['fu_tmax_mean']:.8g} {row['fu_tmax_std']:.8g}\n"
            )
    return plot_path


def typical_xo(values: list[float], rows: list[dict[str, float | int | None]]) -> list[float]:
    chosen = [values[0], values[len(values) // 2], values[-1]]
    finite = [(row["xo"], row["t90_mean"]) for row in rows if row["t90_mean"] is not None]
    if finite:
        xo_min = min(finite, key=lambda item: item[1])[0]
        if all(abs(xo_min - xo) > 1e-12 for xo in chosen):
            chosen.insert(1, xo_min)
    return chosen


def plot_fu(n: int, values: list[float]) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "python" / "plotters" / "plot_fu.py"),
        "--output",
        str(OUT / f"fu_N{n}.png"),
        "--t-max",
        str(TMAX),
    ]
    for xo in values:
        cmd += ["--series", xo_label(xo), str(dump_dir(n, xo))]
    subprocess.check_call(cmd)


def plot_t90(tables: list[tuple[str, Path]]) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "python" / "plotters" / "plot_t90.py"),
        "--output",
        str(OUT / "t90_vs_xo.png"),
    ]
    for label, path in tables:
        cmd += ["--series", label, str(path)]
    subprocess.check_call(cmd)


def run_n(n: int, dt: float, values: list[float]) -> tuple[Path, list[dict[str, float | int | None]], list[str]]:
    rows: list[dict[str, float | int | None]] = []
    missed_lines: list[str] = []
    for xo in values:
        for seed in SEEDS:
            print(f"2.2 N={n} xo={xo:.6g} seed={seed}", flush=True)
            simulate(n, xo, seed, dt)
        row, missed = summarize_folder(n, xo)
        rows.append(row)
        for seed, fu, t_last in missed:
            missed_lines.append(f"{n} {xo:.10g} {seed} {fu:.8g} {t_last:.8g}\n")
            print(f"  missed Fu(tmax)={fu:.3f} seed={seed}", flush=True)
        if row["t90_mean"] is None:
            print(f"  <t90> undefined  Fu(tmax)={row['fu_tmax_mean']:.3f}", flush=True)
        else:
            print(f"  <t90>={row['t90_mean']:.3f}s  std={row['t90_std']:.3f}s", flush=True)
    return write_tables(n, rows), rows, missed_lines


def main() -> None:
    if not EXE.is_file():
        raise SystemExit(f"missing {EXE}")
    if not DT_FILE.is_file():
        raise SystemExit(f"missing {DT_FILE}")
    dt = read_dt()
    print(f"dt={dt:g} from {DT_FILE}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    values = xo_values()
    print("xo", " ".join(f"{xo:.6g}" for xo in values), flush=True)
    table_100, rows_100, missed_100 = run_n(N_MAIN, dt, values)
    table_20, rows_20, missed_20 = run_n(N_LOW, dt, values)
    missed_all = missed_100 + missed_20
    missed_path = OUT / "missed.txt"
    if missed_all:
        missed_path.write_text("N xo seed Fu_tmax t_last\n" + "".join(missed_all), encoding="utf-8")
    elif missed_path.is_file():
        missed_path.unlink()
    plot_fu(N_MAIN, typical_xo(values, rows_100))
    plot_fu(N_LOW, typical_xo(values, rows_20))
    plot_t90([(rf"$N = {N_MAIN}$", table_100), (rf"$N = {N_LOW}$", table_20)])
    FIGS.mkdir(parents=True, exist_ok=True)
    names = [
        "fu_N100.png",
        "fu_N20.png",
        "t90_vs_xo.png",
        "t90_N100.txt",
        "t90_N20.txt",
        "report_N100.txt",
        "report_N20.txt",
        "missed.txt",
    ]
    for name in names:
        src = OUT / name
        if src.is_file():
            shutil.copy2(src, FIGS / name)
    print("done", FIGS, flush=True)


if __name__ == "__main__":
    main()
