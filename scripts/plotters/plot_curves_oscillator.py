import argparse
import math
import sys
from pathlib import Path

from matplotlib.ticker import ScalarFormatter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import new_figure, place_legend_below, save_figure, style_axes, viridis_colors

CURVES = (
    ("euler_pc", "Euler predictor-corrector", "--euler-pc", 3),
    ("verlet", "Verlet", "--verlet", 3),
    ("velocity_verlet", "Velocity Verlet", "--velocity-verlet", 3),
    ("beeman", "Beeman", "--beeman", 3),
    ("analytical", "Analytical", "--analytical", 2),
)


class ScientificFormatter(ScalarFormatter):
    def get_offset(self) -> str:
        offset = super().get_offset()
        if not offset:
            return r"$\times 10^{0}$"
        return offset


def read_curve(path: Path, expected_fields: int, t_first: float | None, t_last: float | None) -> tuple[list[float], list[float]]:
    times: list[float] = []
    positions: list[float] = []
    with path.open(encoding="utf-8") as stream:
        for lineno, raw in enumerate(stream, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != expected_fields:
                raise ValueError(f"{path}:{lineno}: expected {expected_fields} columns, got {len(parts)}")
            try:
                t, x = float(parts[0]), float(parts[1])
            except ValueError:
                raise ValueError(f"{path}:{lineno}: expected numeric time and position") from None
            if not math.isfinite(t) or not math.isfinite(x):
                raise ValueError(f"{path}:{lineno}: time and position must be finite")
            if t_first is not None and t < t_first:
                continue
            if t_last is not None and t > t_last:
                continue
            times.append(t)
            positions.append(x)
    if not times:
        raise ValueError(f"{path}: no samples in the selected time interval")
    return times, positions


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot selected oscillator trajectories as position versus time")
    parser.add_argument("--output", type=Path, required=True, help="output plot path")
    for key, _label, option, _columns in CURVES:
        parser.add_argument(option, dest=key, type=Path, nargs="+", action="append", metavar="TRAJECTORY",
                            help=f"trajectory file(s) for {key.replace('_', ' ')}")
    parser.add_argument("--t_first", type=float, help="first time shown (s)")
    parser.add_argument("--t_last", type=float, help="last time shown (s)")
    args = parser.parse_args()

    if args.t_first is not None and not math.isfinite(args.t_first):
        parser.error("--t_first must be finite")
    if args.t_last is not None and not math.isfinite(args.t_last):
        parser.error("--t_last must be finite")
    if args.t_first is not None and args.t_last is not None and args.t_first >= args.t_last:
        parser.error("--t_first must be less than --t_last")

    selected = [(key, label, columns, getattr(args, key) or []) for key, label, _option, columns in CURVES]
    if not any(paths for _key, _label, _columns, path_groups in selected for paths in path_groups):
        parser.error("provide at least one trajectory option, e.g. --verlet trajectory.txt")

    curve_count = sum(len(group) for _key, _label, _columns, path_groups in selected for group in path_groups)
    colors = viridis_colors(curve_count)
    fig, ax = new_figure()
    curve_index = 0
    try:
        for key, label, columns, path_groups in selected:
            for group in path_groups:
                for path in group:
                    times, positions = read_curve(path, columns, args.t_first, args.t_last)
                    curve_label = label if len(group) == 1 and len(path_groups) == 1 else f"{label}: {path.stem}"
                    ax.plot(times, positions, color=colors[curve_index],
                            label=curve_label, zorder=3)
                    curve_index += 1
    except (OSError, ValueError) as error:
        parser.error(str(error))

    style_axes(ax, "tiempo $t$ (s)", "posición $x$ (m)")
    for axis in (ax.xaxis, ax.yaxis):
        formatter = ScientificFormatter(useMathText=True)
        formatter.set_scientific(True)
        formatter.set_powerlimits((0, 0))
        formatter.set_useOffset(False)
        axis.set_major_formatter(formatter)
    if args.t_first is not None or args.t_last is not None:
        ax.set_xlim(left=args.t_first, right=args.t_last)
    place_legend_below(ax, ncol=min(curve_index, 3))
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()