import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from metrics import mean_std, t90_of_nu
from traj import read_nu_series

EXE = ROOT / "build-local" / "TimeDrivenSim.exe"
DT_FILE = ROOT / "docs" / "results" / "2.1" / "dt.txt"
FIGS = ROOT / "docs" / "results" / "2.4"
WORK = Path(os.environ.get("TEMP", "/tmp")) / "tp4_24b_consigna"
PREV = Path(os.environ.get("TEMP", "/tmp")) / "tp4_22_consigna"
OUT = WORK

R = 0.51
r = 0.0175
XO_MIN = r
XO_MAX = R - r
N_XO = 9
TMAX = 100.0
DT2 = 0.05
REPS = 5
SEEDS = list(range(1, REPS + 1))
N_VALUES = (20, 50, 100, 200, 300, 400)


def xo_values() -> list[float]:
    span = XO_MAX - XO_MIN
    return [XO_MIN + i * span / (N_XO - 1) for i in range(N_XO)]


def xo_tag(xo: float) -> str:
    return f"{xo:.6f}"


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


def dump_dir(root: Path, n: int, xo: float) -> Path:
    return root / "dumps" / f"N{n}" / f"xo{xo_tag(xo)}"


def dump_complete(path: Path, n: int) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        N, series = read_nu_series(path)
    except (OSError, ValueError):
        return False
    return N == n and series[-1][0] + 1e-12 >= TMAX


def locate_dump(n: int, xo: float, seed: int) -> Path | None:
    name = f"run_{seed}.txt"
    for root in (OUT, PREV):
        path = dump_dir(root, n, xo) / name
        if dump_complete(path, n):
            return path
    return None


def simulate(n: int, xo: float, seed: int, dt: float) -> Path:
    found = locate_dump(n, xo, seed)
    if found is not None:
        return found
    folder = dump_dir(OUT, n, xo)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"run_{seed}.txt"
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
            "-init",
            "random",
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


def summarize(n: int, xo: float, paths: list[Path]) -> dict[str, float | int | None]:
    t90s: list[float] = []
    fu_end: list[float] = []
    for path in paths:
        N, series = read_nu_series(path)
        if N != n:
            raise RuntimeError(f"{path}: N={N}, expected {n}")
        t_last, nu_last = series[-1]
        fu_end.append(nu_last / n)
        t90 = t90_of_nu(n, series)
        if t90 is not None:
            t90s.append(t90)
    fu_mean, fu_std = mean_std(fu_end)
    row: dict[str, float | int | None] = {
        "N": n,
        "xo": xo,
        "n_reached": len(t90s),
        "n_total": len(paths),
        "fu_tmax_mean": fu_mean,
        "fu_tmax_std": fu_std,
        "t90_mean": None,
        "t90_std": None,
    }
    if len(t90s) == len(paths):
        mean, std = mean_std(t90s)
        row["t90_mean"] = mean
        row["t90_std"] = std
    return row


def write_grid(path: Path, rows: list[dict[str, float | int | None]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("N xo t90_mean t90_std n_reached n_total fu_tmax_mean fu_tmax_std\n")
        for row in rows:
            t90_mean = "nan" if row["t90_mean"] is None else f"{row['t90_mean']:.8g}"
            t90_std = "nan" if row["t90_std"] is None else f"{row['t90_std']:.8g}"
            fh.write(
                f"{row['N']} {row['xo']:.10g} {t90_mean} {t90_std} "
                f"{row['n_reached']} {row['n_total']} "
                f"{row['fu_tmax_mean']:.8g} {row['fu_tmax_std']:.8g}\n"
            )


def write_optima(path: Path, rows: list[dict[str, float | int | None]]) -> None:
    by_n: dict[int, list[dict[str, float | int | None]]] = {}
    for row in rows:
        if row["t90_mean"] is None or row["n_reached"] != row["n_total"]:
            continue
        by_n.setdefault(int(row["N"]), []).append(row)
    with path.open("w", encoding="utf-8") as fh:
        fh.write("N xo_opt t90_min t90_std\n")
        for n in sorted(by_n):
            best = min(by_n[n], key=lambda item: float(item["t90_mean"]))
            fh.write(f"{n} {best['xo']:.10g} {best['t90_mean']:.8g} {best['t90_std']:.8g}\n")


def plot_heatmap(table: Path) -> None:
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "scripts" / "plotters" / "plot_heatmap.py"),
            "--input",
            str(table),
            "--output",
            str(OUT / "heatmap_t90.png"),
        ]
    )


def main() -> None:
    if not EXE.is_file():
        raise SystemExit(f"missing {EXE}")
    if not DT_FILE.is_file():
        raise SystemExit(f"missing {DT_FILE}")
    dt = read_dt()
    print(f"dt={dt:g} from {DT_FILE}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    values = xo_values()
    rows: list[dict[str, float | int | None]] = []
    for n in N_VALUES:
        for xo in values:
            paths: list[Path] = []
            for seed in SEEDS:
                print(f"2.4b N={n} xo={xo:.6g} seed={seed}", flush=True)
                paths.append(simulate(n, xo, seed, dt))
            row = summarize(n, xo, paths)
            rows.append(row)
            t90 = "nan" if row["t90_mean"] is None else f"{row['t90_mean']:.3f}s"
            print(
                f"  <t90>={t90} ({row['n_reached']}/{row['n_total']})  Fu(tmax)={row['fu_tmax_mean']:.3f}",
                flush=True,
            )
    grid = OUT / "heatmap_t90.txt"
    write_grid(grid, rows)
    write_optima(OUT / "xo_opt.txt", rows)
    plot_heatmap(grid)
    FIGS.mkdir(parents=True, exist_ok=True)
    for name in ("heatmap_t90.png", "heatmap_t90.txt", "xo_opt.txt"):
        src = OUT / name
        if src.is_file():
            shutil.copy2(src, FIGS / name)
    print("done", FIGS, flush=True)


if __name__ == "__main__":
    main()
