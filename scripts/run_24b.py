import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from metrics import mean_std, t90_of_nu
from traj import read_nu_series
from paths import find_executable

EXE = find_executable(ROOT, "TimeDrivenSimTable")
DT_FILE = ROOT / "docs" / "results" / "2.1" / "dt.txt"
FIGS = ROOT / "docs" / "results" / "2.4"
TEMP = Path(os.environ.get("TEMP", "/tmp"))
WORK = TEMP / "tp4_24b_consigna"
PREV = TEMP / "tp4_22_consigna"
FROM_24A = TEMP / "tp4_24_event"
OUT = WORK

R = 0.51
r = 0.0175
XO_MIN = r
XO_MAX = R - r
N_XO = 9
TF = 2000.0
DT2 = 0.05
REPS = 30
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


def has_t90(path: Path, n: int) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        N, series = read_nu_series(path)
    except (OSError, ValueError):
        return False
    return N == n and t90_of_nu(n, series) is not None


def locate_dump(n: int, xo: float, seed: int) -> Path | None:
    name = f"run_{seed}.txt"
    candidates = [
        dump_dir(OUT, n, xo) / name,
        dump_dir(PREV, n, xo) / name,
    ]
    if abs(xo - XO_MIN) < 1e-9:
        candidates.append(FROM_24A / "dumps" / f"N{n}" / name)
    for path in candidates:
        if has_t90(path, n):
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
            str(TF),
            "--until-used",
            "-n",
            str(save_stride(dt)),
            "--out",
            str(path),
        ]
    )
    N, series = read_nu_series(path)
    if N != n or t90_of_nu(n, series) is None:
        raise RuntimeError(f"{path}: Nu={series[-1][1]} did not reach t90")
    return path


def summarize(n: int, xo: float, paths: list[Path]) -> dict[str, float | int]:
    t90s: list[float] = []
    for path in paths:
        N, series = read_nu_series(path)
        if N != n:
            raise RuntimeError(f"{path}: N={N}, expected {n}")
        t90 = t90_of_nu(n, series)
        if t90 is None:
            raise RuntimeError(f"{path}: Nu={series[-1][1]} did not reach t90")
        t90s.append(t90)
    mean, std = mean_std(t90s)
    return {
        "N": n,
        "xo": xo,
        "n_reached": len(t90s),
        "n_total": len(paths),
        "t90_mean": mean,
        "t90_std": std,
    }


def write_grid(path: Path, rows: list[dict[str, float | int]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("N xo t90_mean t90_std n_reached n_total\n")
        for row in rows:
            fh.write(
                f"{row['N']} {row['xo']:.10g} {row['t90_mean']:.8g} {row['t90_std']:.8g} "
                f"{row['n_reached']} {row['n_total']}\n"
            )


def write_optima(path: Path, rows: list[dict[str, float | int]]) -> None:
    by_n: dict[int, list[dict[str, float | int]]] = {}
    for row in rows:
        if row["n_reached"] != row["n_total"]:
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
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "scripts" / "plotters" / "plot_heatmap.py"),
            "--input",
            str(table),
            "--output",
            str(OUT / "heatmap_t90_fila.png"),
            "--per-row",
        ]
    )


def main() -> None:
    if not DT_FILE.is_file():
        raise SystemExit(f"missing {DT_FILE}")
    dt = read_dt()
    print(f"dt={dt:g} from {DT_FILE}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    values = xo_values()
    rows: list[dict[str, float | int]] = []
    for n in N_VALUES:
        for xo in values:
            paths: list[Path] = []
            for seed in SEEDS:
                found = locate_dump(n, xo, seed)
                if found is None:
                    print(f"2.4b N={n} xo={xo:.6g} seed={seed} run", flush=True)
                else:
                    print(f"2.4b N={n} xo={xo:.6g} seed={seed} reuse", flush=True)
                paths.append(simulate(n, xo, seed, dt))
            row = summarize(n, xo, paths)
            rows.append(row)
            print(
                f"  <t90>={row['t90_mean']:.3f}s ({row['n_reached']}/{row['n_total']})",
                flush=True,
            )
    grid = OUT / "heatmap_t90.txt"
    write_grid(grid, rows)
    write_optima(OUT / "xo_opt.txt", rows)
    plot_heatmap(grid)
    FIGS.mkdir(parents=True, exist_ok=True)
    for name in ("heatmap_t90.png", "heatmap_t90_fila.png", "heatmap_t90.txt", "xo_opt.txt"):
        src = OUT / name
        if src.is_file():
            shutil.copy2(src, FIGS / name)
    print("done", FIGS, flush=True)


if __name__ == "__main__":
    main()
