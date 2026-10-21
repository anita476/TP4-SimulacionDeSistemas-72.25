import argparse
from decimal import Decimal, InvalidOperation
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from paths import find_executable

METHODS = ("euler_pc", "verlet", "velocity_verlet", "beeman", "velocity_verlet_vanilla")
MAX_DT_VALUES = 1_000_000
MAX_INTEGRATION_STEPS = 1_000_000_000


def positive_decimal(value: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"invalid number: {value!r}") from None
    if not number.is_finite() or number <= 0:
        raise argparse.ArgumentTypeError("value must be finite and > 0")
    try:
        as_float = float(number)
    except (OverflowError, ValueError):
        as_float = 0.0
    if not (as_float > 0 and as_float < float("inf")):
        raise argparse.ArgumentTypeError("value must be representable as a finite positive double")
    return number


def dt_values(dt_max: Decimal, dt_min: Decimal, dt_step: Decimal, mode: str = "log") -> list[Decimal]:
    if dt_max < dt_min:
        raise ValueError("--dt-max must be greater than or equal to --dt-min")
    if mode == "linear":
        count = int((dt_max - dt_min) // dt_step) + 1
        if count > MAX_DT_VALUES:
            raise ValueError(f"dt sweep has {count} values; maximum is {MAX_DT_VALUES}")
        return [dt_max - index * dt_step for index in range(count)]
    if dt_step >= 1:
        raise ValueError("in log mode, --dt-step must be a factor between 0 and 1, e.g. 1e-1")

    values = [dt_max]
    while values[-1] > dt_min:
        if len(values) >= MAX_DT_VALUES:
            raise ValueError(f"dt sweep exceeds {MAX_DT_VALUES} values")
        next_dt = values[-1] * dt_step
        values.append(max(next_dt, dt_min))
    return values


def dt_tag(dt: Decimal) -> str:
    return format(dt.normalize(), "g").replace("+", "")


def run_simulation(executable: Path, args: list[str]) -> None:
    command = [str(executable), *args]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"{' '.join(command)}\n{detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep oscillator integration methods over decreasing dt values")
    parser.add_argument("--out_dir", type=Path, required=True, help="directory where method subdirectories and trajectories are saved")
    parser.add_argument("--dt-max", required=True, type=positive_decimal, help="largest time step (s), e.g. 1e-2")
    parser.add_argument("--dt-min", required=True, type=positive_decimal, help="smallest time step (s), e.g. 1e-4")
    parser.add_argument("--dt-step", required=True, type=positive_decimal, help="log mode: multiplicative factor < 1; linear mode: decrement")
    parser.add_argument("--dt-mode", choices=("log", "linear"), default="log", help="dt sweep spacing (default: logarithmic)")
    parser.add_argument("--runs", type=int, default=5, help="repetitions for each method and dt (default: 5)")
    parser.add_argument("--tf", type=float, default=5.0, help="final simulation time in seconds (default: 5)")
    parser.add_argument("--m", type=float, default=70.0, help="mass in kg (default: 70)")
    parser.add_argument("--k", type=float, default=1.0e4, help="spring constant in N/m (default: 10000)")
    parser.add_argument("--gamma", type=float, default=100.0, help="damping in kg/s (default: 100)")
    parser.add_argument("--A", type=float, default=1.0, help="initial amplitude in m (default: 1)")
    parser.add_argument("--bin", type=Path, help="oscillator executable (default: find it under build/ or build-local/)")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be >= 1")
    if not (math.isfinite(args.tf) and args.tf > 0 and math.isfinite(args.m) and args.m > 0
            and math.isfinite(args.k) and args.k > 0 and math.isfinite(args.gamma) and args.gamma >= 0):
        parser.error("--tf, --m and --k must be > 0, and --gamma must be >= 0")
    return args


def main() -> int:
    args = parse_args()
    try:
        steps = dt_values(args.dt_max, args.dt_min, args.dt_step, args.dt_mode)
        minimum_allowed_dt = Decimal(str(args.tf)) / MAX_INTEGRATION_STEPS
        if min(steps) < minimum_allowed_dt:
            raise ValueError(
                f"dt={min(steps)} requires more than {MAX_INTEGRATION_STEPS:.0e} integration steps "
                f"for tf={args.tf:g}; the C++ integrator rejects it (minimum dt is {minimum_allowed_dt})"
            )
        executable = args.bin or find_executable(ROOT, "TimeDrivenSimOscillator")
        if not executable.is_file():
            raise FileNotFoundError(f"executable not found: {executable}")
        args.out_dir.mkdir(parents=True, exist_ok=True)

        total = len(METHODS) * len(steps) * args.runs
        completed = 0
        for method in METHODS:
            method_dir = args.out_dir / method
            method_dir.mkdir(parents=True, exist_ok=True)
            for dt in steps:
                for run_number in range(1, args.runs + 1):
                    trajectory = method_dir / f"{method}_{dt_tag(dt)}_{run_number}.txt"
                    run_simulation(
                        executable,
                        [
                            "-method", method,
                            "-dt", format(dt, "g"),
                            "-tf", format(args.tf, ".17g"),
                            "-m", format(args.m, ".17g"),
                            "-k", format(args.k, ".17g"),
                            "-gamma", format(args.gamma, ".17g"),
                            "-A", format(args.A, ".17g"),
                            "--out", str(trajectory),
                        ],
                    )
                    completed += 1
                    print(f"[{completed}/{total}] {method} dt={dt} run={run_number} -> {trajectory}", flush=True)
        return 0
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())