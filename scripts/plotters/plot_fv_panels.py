import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import matplotlib
from matplotlib.colors import to_rgb

from plot_style import FIGURE_SIZE, FONT_SIZE, SERIES, apply_academic_style, save_figure
from speed import mb_pdf


def load_pdf(path: Path) -> tuple[list[float], list[float], list[float]]:
    """Read 'v f_mean f_std' (bin centers) and rebuild the bin edges."""
    centers: list[float] = []
    means: list[float] = []
    stds: list[float] = []
    header = None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if header is None:
                header = parts
                if header[:3] != ["v", "f_mean", "f_std"]:
                    raise ValueError(f"{path}: expected columns v f_mean f_std")
                continue
            centers.append(float(parts[0]))
            means.append(float(parts[1]))
            stds.append(float(parts[2]))
    if len(centers) < 2:
        raise ValueError(f"{path}: need at least 2 bins")
    width = centers[1] - centers[0]
    for a, b in zip(centers, centers[1:]):
        if abs((b - a) - width) > 1e-9 * max(1.0, width):
            raise ValueError(f"{path}: bins are not uniform")
    edges = [c - 0.5 * width for c in centers] + [centers[-1] + 0.5 * width]
    return edges, means, stds


def tint(color: str, towards_white: float) -> tuple[float, float, float]:
    """Blend a series color toward white so a filled area reads like a line of the same color."""
    r, g, b = to_rgb(color)
    return (r + (1 - r) * towards_white, g + (1 - g) * towards_white, b + (1 - b) * towards_white)


def main() -> None:
    parser = argparse.ArgumentParser(description="2.3: one panel per instant, shared axes, bar histograms with error bars")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--panel", nargs=2, action="append", metavar=("LABEL", "TABLE"), required=True)
    parser.add_argument("--fit", type=float, default=None, help="kBT (J): draw the 2D Maxwell-Boltzmann reference")
    parser.add_argument("--m", type=float, default=None, help="particle mass (kg); required with --fit")
    parser.add_argument("--vline", nargs=2, metavar=("V", "LABEL"), default=None, help="initial speed marker")
    parser.add_argument("--xmax", type=float, default=None)
    parser.add_argument("--ncols", type=int, default=2)
    args = parser.parse_args()
    if args.fit is not None and (args.m is None or not (args.m > 0.0) or not (args.fit > 0.0)):
        parser.error("--fit > 0 and --m > 0 go together")
    if args.ncols < 1:
        parser.error("--ncols must be >= 1")

    apply_academic_style()
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(args.panel)
    ncols = min(args.ncols, n)
    nrows = math.ceil(n / ncols)
    figsize = FIGURE_SIZE if n == 1 else (4.8 * ncols, 3.9 * nrows)
    fig, axes = plt.subplots(nrows, ncols, sharex=True, sharey=True, figsize=figsize, layout="constrained")
    axes = [axes] if n == 1 else list(axes.flat)

    ymax = 0.0
    xmax = args.xmax if args.xmax is not None else 0.0
    try:
        for i, (ax, (label, table)) in enumerate(zip(axes, args.panel)):
            edges, means, stds = load_pdf(Path(table))
            width = edges[1] - edges[0]
            centers = [0.5 * (a + b) for a, b in zip(edges, edges[1:])]
            hi = [m + s for m, s in zip(means, stds)]
            series_color = SERIES[i % len(SERIES)]
            ax.bar(
                centers,
                means,
                width=width,
                yerr=stds,
                color=tint(series_color, 0.4),
                edgecolor=series_color,
                linewidth=1.0,
                error_kw={"ecolor": series_color, "elinewidth": 1.2, "capsize": 2.5, "capthick": 1.2},
                zorder=2,
            )
            ax.set_title(label, fontsize=FONT_SIZE, pad=8)
            ymax = max(ymax, max(hi))
            if args.xmax is None:
                xmax = max(xmax, edges[-1])
    except (OSError, ValueError) as error:
        parser.error(str(error))
    for ax in axes[n:]:
        ax.set_visible(False)

    if args.vline is not None:
        v0, v0_label = float(args.vline[0]), args.vline[1]
        for ax in axes[:n]:
            ax.axvline(v0, color="black", linestyle=":", zorder=1, label=v0_label)
    if args.fit is not None:
        curve_v = [xmax * i / 400 for i in range(401)]
        curve_f = [mb_pdf(v, args.m, args.fit) for v in curve_v]
        for ax in axes[:n]:
            ax.plot(curve_v, curve_f, color="black", linestyle="--", linewidth=1.4, zorder=4, label=rf"$k_B T^* = {args.fit:.3g}\,\mathrm{{J}}$")
        ymax = max(ymax, max(curve_f))

    axes[0].set_xlim(0.0, xmax)
    axes[0].set_ylim(0.0, ymax * 1.08)
    for i, ax in enumerate(axes[:n]):
        if i // ncols == nrows - 1 or i + ncols >= n:
            ax.set_xlabel(r"módulo de la velocidad $v$ (m/s)", labelpad=8)
        if i % ncols == 0:
            ax.set_ylabel(r"$f(v)$ (s/m)", labelpad=8)
    handles, labels = axes[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="outside lower center", ncol=len(handles), frameon=True, fontsize=FONT_SIZE, borderaxespad=0.6)
        fig.get_layout_engine().set(h_pad=0.15, hspace=0.06)
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()