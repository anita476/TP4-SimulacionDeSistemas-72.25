import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python" / "lib"))

from energy import max_relative_drift
from metrics import mean_std
from traj import read_traj

EXE = ROOT / "build-local" / "TimeDrivenSim.exe"
TP3_EXE = ROOT.parent / "TP3-SimulacionDeSistemas-72.25" / "build-local" / "EventDrivenSim.exe"
FIGS = ROOT / "data" / "2.1"
WORK = Path(os.environ.get("TEMP", "/tmp")) / "tp4_21_consigna"
OUT = WORK

N_ENERGY = 300
ENERGY_TF = 5.0
DT2 = 0.01
DTS = (1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 5e-3)
DRIFT_LIMIT = 0.01
N_RUNTIME = (50, 100, 200, 300, 400, 500, 650)
RUNTIME_TF = 30.0
REPS = 10
XO = 0.0175
SEEDS = list(range(1, REPS + 1))


def dt_label(dt: float) -> str:
    exponent = int(math.floor(math.log10(dt)))
    mantissa = dt / 10 ** exponent
    if abs(mantissa - 1.0) < 1e-9:
        return rf"$dt = 10^{{{exponent}}}\,\mathrm{{s}}$"
    return rf"$dt = {mantissa:g}\times10^{{{exponent}}}\,\mathrm{{s}}$"


def save_stride(dt: float) -> int:
    return max(1, int(round(DT2 / dt)))


def run_tp4(args: list[str]) -> None:
    cmd = [str(EXE), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(cmd)}\n{detail}")


def timed_seconds(cmd: list[str]) -> float:
    start = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    elapsed = time.perf_counter() - start
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(cmd)}\n{detail}")
    return elapsed


def write_table(path: Path, ns: list[int], means: list[float], stds: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        fh.write("N t_mean t_std\n")
        for n, mean, std in zip(ns, means, stds):
            fh.write(f"{n} {mean:.8g} {std:.8g}\n")


def energy_dump(dt: float) -> Path:
    return OUT / "dumps" / f"energy_N{N_ENERGY}_dt{dt:.0e}.txt"


def run_energy() -> tuple[list[float], list[Path]]:
    OUT.joinpath("dumps").mkdir(parents=True, exist_ok=True)
    dts: list[float] = []
    dumps: list[Path] = []
    for dt in DTS:
        path = energy_dump(dt)
        print(f"2.1a N={N_ENERGY} dt={dt:g} tf={ENERGY_TF} -> {path.name}", flush=True)
        try:
            run_tp4(
                [
                    "-N",
                    str(N_ENERGY),
                    "-seed",
                    "1",
                    "-dt",
                    f"{dt:.10g}",
                    "-tf",
                    str(ENERGY_TF),
                    "-n",
                    str(save_stride(dt)),
                    "--out",
                    str(path),
                ]
            )
        except RuntimeError as error:
            print(f"  skipped: {error}", flush=True)
            if path.exists():
                path.unlink()
            continue
        dts.append(dt)
        dumps.append(path)
        print(f"  drift={max_relative_drift(read_traj(path)):.4g}", flush=True)
    if not dumps:
        raise RuntimeError("no energy dump completed")
    return dts, dumps


def choose_dt(dts: list[float], dumps: list[Path]) -> float:
    kept: list[tuple[float, float]] = []
    for dt, dump in zip(dts, dumps):
        drift = max_relative_drift(read_traj(dump))
        kept.append((dt, drift))
        print(f"dt={dt:g}  max |E-E0|/|E0| = {drift:.4g}", flush=True)
    good = [dt for dt, drift in kept if drift <= DRIFT_LIMIT]
    chosen = max(good) if good else min(dt for dt, _drift in kept)
    print(f"chosen dt={chosen:g} (largest with drift <= {DRIFT_LIMIT:g})", flush=True)
    return chosen


def plot_energy(dts: list[float], dumps: list[Path]) -> None:
    cmd = [sys.executable, str(ROOT / "python" / "plotters" / "plot_energy.py"), "--output", str(OUT / "energia_vs_t.png")]
    for dt, dump in zip(dts, dumps):
        cmd += ["--series", dt_label(dt), str(dump)]
    subprocess.check_call(cmd)
    cmd = [sys.executable, str(ROOT / "python" / "plotters" / "plot_energy_dt.py"), "--output", str(OUT / "deriva_vs_dt.png")]
    for dt, dump in zip(dts, dumps):
        cmd += ["--point", f"{dt:.10g}", str(dump)]
    subprocess.check_call(cmd)


def tp4_init(n: int) -> str:
    return "hex" if n > 400 else "random"


def run_tp4_times(dt: float) -> Path:
    path = OUT / "times_td.txt"
    ns: list[int] = []
    means: list[float] = []
    stds: list[float] = []
    for n in N_RUNTIME:
        times: list[float] = []
        init = tp4_init(n)
        for seed in SEEDS:
            elapsed = timed_seconds(
                [
                    str(EXE),
                    "-N",
                    str(n),
                    "-seed",
                    str(seed),
                    "-xo",
                    str(XO),
                    "-init",
                    init,
                    "-dt",
                    f"{dt:.10g}",
                    "-tf",
                    str(RUNTIME_TF),
                    "-n",
                    str(save_stride(dt)),
                ]
            )
            times.append(elapsed)
            print(f"2.1b N={n} seed={seed} init={init} {elapsed:.3f}s", flush=True)
        mean, std = mean_std(times)
        ns.append(n)
        means.append(mean)
        stds.append(std)
        print(f"  mean={mean:.3f}s  std={std:.3f}s", flush=True)
    write_table(path, ns, means, stds)
    return path


def tp3_init(n: int) -> str:
    return "hex" if n >= 400 else "random"


def run_tp3_times() -> Path:
    if not TP3_EXE.is_file():
        raise RuntimeError(f"missing {TP3_EXE}")
    path = OUT / "times_ed.txt"
    ns: list[int] = []
    means: list[float] = []
    stds: list[float] = []
    for n in N_RUNTIME:
        times: list[float] = []
        init = tp3_init(n)
        for seed in SEEDS:
            elapsed = timed_seconds(
                [
                    str(TP3_EXE),
                    "-N",
                    str(n),
                    "-seed",
                    str(seed),
                    "-tmax",
                    str(RUNTIME_TF),
                    "-init",
                    init,
                    "--raw",
                ]
            )
            times.append(elapsed)
            print(f"TP3 1.1 N={n} seed={seed} init={init} {elapsed:.3f}s", flush=True)
        mean, std = mean_std(times)
        ns.append(n)
        means.append(mean)
        stds.append(std)
        print(f"  mean={mean:.3f}s  std={std:.3f}s", flush=True)
    write_table(path, ns, means, stds)
    return path


def plot_runtime(td: Path, ed: Path) -> None:
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "python" / "plotters" / "plot_runtime.py"),
            "--output",
            str(OUT / "tiempo_vs_N.png"),
            "--series",
            "paso temporal",
            str(td),
            "--series",
            "eventos",
            str(ed),
        ]
    )


def animate(dt: float) -> None:
    dump = OUT / "dumps" / "animacion.txt"
    print("animation dump", dump.name, flush=True)
    run_tp4(
        [
            "-N",
            "100",
            "-seed",
            "1",
            "-xo",
            str(XO),
            "-dt",
            f"{dt:.10g}",
            "-tf",
            "8",
            "-n",
            str(max(1, int(round(0.08 / dt)))),
            "--out",
            str(dump),
        ]
    )
    animate_py = ROOT / "python" / "animate.py"
    subprocess.check_call(
        [sys.executable, str(animate_py), "--traj", str(dump), "--png", str(OUT / "cuadro_inicial.png"), "--frame", "0"]
    )
    subprocess.check_call(
        [sys.executable, str(animate_py), "--traj", str(dump), "--out", str(OUT / "animacion.gif"), "--fps", "12"]
    )


def main() -> None:
    if not EXE.is_file():
        raise SystemExit(f"missing {EXE}")
    OUT.mkdir(parents=True, exist_ok=True)
    dts, dumps = run_energy()
    plot_energy(dts, dumps)
    dt = choose_dt(dts, dumps)
    (OUT / "dt.txt").write_text(f"{dt:.10g}\n", encoding="utf-8")
    td = run_tp4_times(dt)
    ed = run_tp3_times()
    plot_runtime(td, ed)
    animate(dt)
    FIGS.mkdir(parents=True, exist_ok=True)
    for name in ("energia_vs_t.png", "deriva_vs_dt.png", "tiempo_vs_N.png", "cuadro_inicial.png", "animacion.gif",
                 "times_td.txt", "times_ed.txt", "dt.txt"):
        src = OUT / name
        if src.is_file():
            shutil.copy2(src, FIGS / name)
    print("done", FIGS, flush=True)


if __name__ == "__main__":
    main()
