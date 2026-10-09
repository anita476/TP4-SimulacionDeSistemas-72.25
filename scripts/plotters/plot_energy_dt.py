import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from energy import max_relative_drift
from plot_style import BLUE, new_figure, save_figure, style_axes
from traj import read_traj


def main() -> None:
    parser = argparse.ArgumentParser(
        description="2.1a: max relative energy drift vs dt"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--point", nargs=2, action="append", metavar=("DT", "DUMP"), required=True)
    args = parser.parse_args()

    dts: list[float] = []
    drifts: list[float] = []
    try:
        for dt_text, dump in args.point:
            dt = float(dt_text)
            if not (dt > 0.0):
                parser.error("dt must be > 0")
            dts.append(dt)
            drifts.append(max_relative_drift(read_traj(dump)))
    except (OSError, ValueError) as error:
        parser.error(str(error))

    order = sorted(range(len(dts)), key=lambda i: dts[i])
    dts = [dts[i] for i in order]
    drifts = [drifts[i] for i in order]

    fig, ax = new_figure()
    ax.plot(dts, drifts, color=BLUE, marker="o", markeredgecolor="black", markeredgewidth=0.6, zorder=3)
    ax.set_xscale("log")
    if all(drift > 0.0 for drift in drifts):
        ax.set_yscale("log")
    style_axes(ax, r"paso temporal $dt$ (s)", r"deriva relativa máxima de $E$")
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()
