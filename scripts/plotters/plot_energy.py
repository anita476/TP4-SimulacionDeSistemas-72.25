import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from energy import energy_series
from plot_style import SERIES, new_figure, place_legend_below, save_figure, style_axes
from traj import read_traj

# Colors of the 2.1 comparison, keyed by the legend label, so dropping a curve does not recolor the rest.
SERIES_COLOR = {
    r"$dt = 10^{-5}\,\mathrm{s}$": SERIES[0],
    r"$dt = 10^{-4}\,\mathrm{s}$": SERIES[1],
    r"$dt = 2\times10^{-4}\,\mathrm{s}$": SERIES[2],
    r"$dt = 3\times10^{-4}\,\mathrm{s}$": SERIES[3],
    r"$dt = 4\times10^{-4}\,\mathrm{s}$": SERIES[4],
    r"$dt = 5\times10^{-4}\,\mathrm{s}$": "#882255",
}
V0 = 1.0
REFERENCE_LABEL = r"$dt = 10^{-5}\,\mathrm{s}$"


def main() -> None:
    parser = argparse.ArgumentParser(description="2.1a: total energy vs time for several dt")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--series", nargs=2, action="append", metavar=("LABEL", "DUMP"), required=True)
    args = parser.parse_args()

    fig, ax = new_figure()
    t_end = 0.0
    theory = None
    try:
        for i, (label, dump) in enumerate(args.series):
            traj = read_traj(dump)
            if traj.m is None:
                parser.error(f"{dump}: m is required for the theoretical energy")
            series_theory = 0.5 * traj.N * traj.m * V0 * V0
            if theory is None:
                theory = series_theory
            elif abs(series_theory - theory) > 1e-9:
                parser.error(f"{dump}: theoretical energy {series_theory} differs from {theory}")
            series = energy_series(traj)
            times = [t for t, _energy in series]
            energies = [energy for _t, energy in series]
            t_end = max(t_end, times[-1])
            on_top = label == REFERENCE_LABEL
            ax.plot(
                times,
                energies,
                color=SERIES_COLOR.get(label, SERIES[i % len(SERIES)]),
                zorder=4 if on_top else 3,
                label=label,
            )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if theory is None:
        parser.error("no series to plot")
    style_axes(ax, "tiempo (s)", "energía total (J)")
    right = t_end if t_end > 0 else 1.0
    ax.set_xlim(0, right)
    (reference,) = ax.plot(
        [0.0, right * 1.07],
        [theory, theory],
        color="black",
        linestyle=":",
        linewidth=1.6,
        zorder=2,
        clip_on=False,
    )
    reference.set_in_layout(False)
    tag = ax.text(
        1.09,
        theory,
        r"$E_0$",
        transform=ax.get_yaxis_transform(),
        va="center",
        ha="left",
        clip_on=False,
        zorder=5,
    )
    place_legend_below(ax, ncol=min(len(args.series), 3))
    save_figure(fig, args.output, extra=(tag,))


if __name__ == "__main__":
    main()
