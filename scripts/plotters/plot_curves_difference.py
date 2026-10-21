import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import SERIES, new_figure, save_figure, style_axes

METHODS = (
    ("euler_pc", "Euler predictor-corrector"),
    ("verlet", "Verlet"),
    ("velocity_verlet", "Velocity Verlet"),
    ("beeman", "Beeman"),
    ("velocity_verlet_vanilla", "Velocity Verlet Vanilla"),
)


def read_difference(
    path: Path, t_first: float | None, t_last: float | None
) -> tuple[list[float], list[float]]:
    times: list[float] = []
    differences: list[float] = []
    with path.open(encoding="utf-8") as stream:
        for lineno, raw in enumerate(stream, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 3:
                raise ValueError(f"{path}:{lineno}: expected 3 columns, got {len(parts)}")
            try:
                t, x_method, x_analytical = map(float, parts)
            except ValueError:
                raise ValueError(f"{path}:{lineno}: expected numeric time and positions") from None
            if not all(math.isfinite(value) for value in (t, x_method, x_analytical)):
                raise ValueError(f"{path}:{lineno}: time and positions must be finite")
            if t_first is not None and t < t_first:
                continue
            if t_last is not None and t > t_last:
                continue
            times.append(t)
            differences.append(x_method - x_analytical)
    if not times:
        raise ValueError(f"{path}: no samples in the selected time interval")
    return times, differences


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot oscillator position differences against the analytical solution"
    )
    parser.add_argument("--output", type=Path, required=True, help="output plot path")
    for method, label in METHODS:
        parser.add_argument(
            f"--{method}",
            dest=method,
            type=Path,
            nargs="+",
            action="append",
            metavar="TRAJECTORY",
            help=f"trajectory file(s) for {label}",
        )
    parser.add_argument("--t_first", type=float, help="first time shown (s)")
    parser.add_argument("--t_last", type=float, help="last time shown (s)")
    args = parser.parse_args()

    if args.t_first is not None and not math.isfinite(args.t_first):
        parser.error("--t_first must be finite")
    if args.t_last is not None and not math.isfinite(args.t_last):
        parser.error("--t_last must be finite")
    if args.t_first is not None and args.t_last is not None and args.t_first >= args.t_last:
        parser.error("--t_first must be less than --t_last")

    selected = [
        (method, label, getattr(args, method) or [])
        for method, label in METHODS
    ]
    if not any(groups for _method, _label, groups in selected):
        parser.error("provide at least one method option, e.g. --verlet trajectory.txt")

    fig, ax = new_figure()
    curve_index = 0
    try:
        for _method, label, path_groups in selected:
            for group in path_groups:
                for path in group:
                    times, differences = read_difference(path, args.t_first, args.t_last)
                    curve_label = (
                        label
                        if len(group) == 1 and len(path_groups) == 1
                        else f"{label}: {path.stem}"
                    )
                    ax.plot(
                        times,
                        differences,
                        color=SERIES[curve_index % len(SERIES)],
                        label=curve_label,
                        zorder=3,
                    )
                    curve_index += 1
    except (OSError, ValueError) as error:
        parser.error(str(error))

    ax.axhline(0.0, color="black", linewidth=1.0, linestyle="--", zorder=2)
    style_axes(ax, "tiempo $t$ (s)", r"$x_{\mathrm{método}} - x_{\mathrm{analítica}}$ (m)")
    if args.t_first is not None or args.t_last is not None:
        ax.set_xlim(left=args.t_first, right=args.t_last)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=min(curve_index, 2))
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()
