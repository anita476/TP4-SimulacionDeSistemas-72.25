import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from energy import energy_series
from plot_style import SERIES, new_figure, place_legend_below, save_figure, style_axes
from traj import read_traj


def main() -> None:
    parser = argparse.ArgumentParser(description="2.1a: total energy vs time for several dt")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--series", nargs=2, action="append", metavar=("LABEL", "DUMP"), required=True)
    args = parser.parse_args()

    fig, ax = new_figure()
    t_end = 0.0
    try:
        for i, (label, dump) in enumerate(args.series):
            traj = read_traj(dump)
            series = energy_series(traj)
            times = [t for t, _energy in series]
            energies = [energy for _t, energy in series]
            t_end = max(t_end, times[-1])
            ax.plot(times, energies, color=SERIES[i % len(SERIES)], zorder=3, label=label)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    style_axes(ax, "tiempo (s)", "energía total (J)")
    ax.set_xlim(0, t_end if t_end > 0 else 1.0)
    place_legend_below(ax, ncol=min(len(args.series), 3))
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()
