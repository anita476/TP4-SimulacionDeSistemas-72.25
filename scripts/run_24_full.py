import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from metrics import mean_std, t100_of_nu, t90_of_nu
from traj import read_nu_series

EXE = ROOT / "build-local" / "TimeDrivenSim.exe"
DT_FILE = ROOT / "docs" / "results" / "2.1" / "dt.txt"
FIGS = ROOT / "docs" / "results" / "2.4"
WORK = Path(os.environ.get("TEMP", "/tmp")) / "tp4_24_full"
OUT = WORK

R = 0.51
r = 0.0175
XO = r
TF = 2000.0
STALL = 60.0
DT2 = 0.05
REPS = 10
SEEDS = list(range(1, REPS + 1))
N_RUNTIME = (50, 100, 200, 300, 400, 500, 650)


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


def last_increase(series: list[tuple[float, int]]) -> float:
    last_t = series[0][0]
    previous = -1
    for t, nu in series:
        if nu != previous:
            last_t = t
            previous = nu
    return last_t


def run_finished(path: Path, n: int) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        N, series = read_nu_series(path)
    except (OSError, ValueError):
        return False
    if N != n:
        return False
    t_last, nu_last = series[-1]
    if nu_last == n:
        return True
    if t_last + 1e-9 >= TF:
        quiet = t_last - last_increase(series)
        if quiet + 1e-9 < STALL:
            raise RuntimeError(
                f"{path}: reached t={t_last:.3g}s with Nu={nu_last}/{n} still increasing"
            )
        return True
    return t_last - last_increase(series) + 1e-9 >= STALL


def simulate(n: int, seed: int, dt: float) -> Path:
    folder = dump_dir(n)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"run_{seed}.txt"
    if run_finished(path, n):
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
            "-n",
            str(save_stride(dt)),
            "-stall",
            str(STALL),
            "--until-used",
            "--out",
            str(path),
        ]
    )
    if not run_finished(path, n):
        raise RuntimeError(f"{path}: run stopped before Nu={n} and before a {STALL:g}s stall")
    return path


def summarize(n: int) -> tuple[dict[str, float | int | None], list[str]]:
    t90s: list[float] = []
    t100s: list[float] = []
    fu_end: list[float] = []
    t_end: list[float] = []
    missed: list[str] = []
    for seed in SEEDS:
        path = dump_dir(n) / f"run_{seed}.txt"
        N, series = read_nu_series(path)
        if N != n:
            raise RuntimeError(f"{path}: N={N}, expected {n}")
        t_last, nu_last = series[-1]
        fu = nu_last / n
        fu_end.append(fu)
        t_end.append(t_last)
        t90 = t90_of_nu(n, series)
        t100 = t100_of_nu(n, series)
        if t90 is None:
            missed.append(f"{n} {seed} t90 {fu:.8g} {t_last:.8g}\n")
        else:
            t90s.append(t90)
        if t100 is None:
            missed.append(f"{n} {seed} t100 {fu:.8g} {t_last:.8g}\n")
        else:
            t100s.append(t100)
    fu_mean, fu_std = mean_std(fu_end)
    tend_mean, tend_std = mean_std(t_end)
    row: dict[str, float | int | None] = {
        "N": n,
        "phi": packing_phi(n),
        "n_t90": len(t90s),
        "n_t100": len(t100s),
        "fu_end_mean": fu_mean,
        "fu_end_std": fu_std,
        "t_end_mean": tend_mean,
        "t_end_std": tend_std,
        "t90_mean": None,
        "t90_std": None,
        "t100_mean": None,
        "t100_std": None,
    }
    if len(t90s) == REPS:
        mean, std = mean_std(t90s)
        row["t90_mean"] = mean
        row["t90_std"] = std
    if len(t100s) == REPS:
        mean, std = mean_std(t100s)
        row["t100_mean"] = mean
        row["t100_std"] = std
    return row, missed


def write_observable(
    path: Path,
    rows: list[dict[str, float | int | None]],
    mean_key: str,
    std_key: str,
    count_key: str,
) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("N phi t_mean t_std\n")
        for row in rows:
            if row[mean_key] is None or row[count_key] != REPS:
                continue
            fh.write(f"{row['N']} {row['phi']:.10g} {row[mean_key]:.8g} {row[std_key]:.8g}\n")


def write_report(path: Path, rows: list[dict[str, float | int | None]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write(
            "N phi n_t90 t90_mean t90_std n_t100 t100_mean t100_std "
            "fu_end_mean fu_end_std t_end_mean t_end_std\n"
        )
        for row in rows:
            def cell(key: str) -> str:
                value = row[key]
                return "nan" if value is None else f"{value:.8g}"

            fh.write(
                f"{row['N']} {row['phi']:.10g} {row['n_t90']} {cell('t90_mean')} {cell('t90_std')} "
                f"{row['n_t100']} {cell('t100_mean')} {cell('t100_std')} "
                f"{row['fu_end_mean']:.8g} {row['fu_end_std']:.8g} "
                f"{row['t_end_mean']:.8g} {row['t_end_std']:.8g}\n"
            )


def data_rows(path: Path) -> int:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    return max(0, len(lines) - 1)


def plot_series(output: Path, series: list[tuple[str, Path]]) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "plotters" / "plot_density.py"),
        "--output",
        str(output),
        "--xlabel",
        r"densidad $\phi$",
        "--ylabel",
        "tiempo (s)",
    ]
    for label, path in series:
        if data_rows(path) > 0:
            cmd += ["--series", label, str(path)]
    if "--series" not in cmd:
        raise RuntimeError(f"no data series for {output}")
    subprocess.check_call(cmd)


def main() -> None:
    if not EXE.is_file():
        raise SystemExit(f"missing {EXE}")
    if not DT_FILE.is_file():
        raise SystemExit(f"missing {DT_FILE}")
    dt = read_dt()
    print(f"dt={dt:g} from {DT_FILE}  ceiling={TF:g}s  stall={STALL:g}s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | int | None]] = []
    missed_lines: list[str] = []
    for n in N_RUNTIME:
        init = tp4_init(n)
        for seed in SEEDS:
            print(f"2.4 full N={n} seed={seed} init={init} xo=r", flush=True)
            simulate(n, seed, dt)
        row, missed = summarize(n)
        rows.append(row)
        missed_lines.extend(missed)
        t90 = "nan" if row["t90_mean"] is None else f"{row['t90_mean']:.3f}s"
        t100 = "nan" if row["t100_mean"] is None else f"{row['t100_mean']:.3f}s"
        print(
            f"  phi={row['phi']:.4g}  <t90>={t90} ({row['n_t90']}/{REPS})  "
            f"<t100>={t100} ({row['n_t100']}/{REPS})  "
            f"Fu(end)={row['fu_end_mean']:.3f}  t_end={row['t_end_mean']:.1f}s",
            flush=True,
        )

    t90_path = OUT / "t90_vs_phi_full.txt"
    t100_path = OUT / "t100_vs_phi_full.txt"
    write_observable(t90_path, rows, "t90_mean", "t90_std", "n_t90")
    write_observable(t100_path, rows, "t100_mean", "t100_std", "n_t100")
    write_report(OUT / "report_full.txt", rows)
    missed_path = OUT / "missed_full.txt"
    if missed_lines:
        missed_path.write_text("N seed observable Fu_end t_end\n" + "".join(missed_lines), encoding="utf-8")
    elif missed_path.is_file():
        missed_path.unlink()

    series: list[tuple[str, Path]] = []
    if data_rows(t90_path) >= 1:
        series.append((r"$t_{90}$", t90_path))
    if data_rows(t100_path) >= 1:
        series.append((r"$t_{100}$", t100_path))
    plot_path = OUT / "t90_t100_vs_phi.png"
    if series:
        plot_series(plot_path, series)
    elif plot_path.is_file():
        plot_path.unlink()

    FIGS.mkdir(parents=True, exist_ok=True)
    for name in (
        "t90_t100_vs_phi.png",
        "t90_vs_phi_full.txt",
        "t100_vs_phi_full.txt",
        "report_full.txt",
        "missed_full.txt",
    ):
        src = OUT / name
        if src.is_file():
            shutil.copy2(src, FIGS / name)
    print("done", FIGS, flush=True)


if __name__ == "__main__":
    main()
