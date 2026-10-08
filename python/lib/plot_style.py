from pathlib import Path

import matplotlib
from matplotlib.collections import LineCollection, PathCollection

FONT_SIZE = 20
FIGURE_SIZE = (6.5, 5.4)
SAVE_DPI = 300

BLUE = "#0072B2"
VERMILLION = "#D55E00"
GREEN = "#009E73"
PURPLE = "#CC79A7"
ORANGE = "#E69F00"
SERIES = (BLUE, VERMILLION, GREEN, PURPLE, ORANGE)
MARKERS = ("o", "s", "D", "^", "v")

_CORNERS = ("upper right", "upper left", "lower right", "lower left")
_LEGEND_PAD = 0.03
_HITS_MAX = 2


def apply_academic_style() -> None:
    matplotlib.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": FONT_SIZE,
            "axes.labelsize": FONT_SIZE,
            "axes.titlesize": FONT_SIZE,
            "axes.linewidth": 1.15,
            "axes.formatter.use_mathtext": True,
            "axes.formatter.limits": (-2, 4),
            "xtick.labelsize": FONT_SIZE,
            "ytick.labelsize": FONT_SIZE,
            "xtick.major.size": 6,
            "ytick.major.size": 6,
            "xtick.major.width": 1.1,
            "ytick.major.width": 1.1,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.fontsize": FONT_SIZE,
            "legend.frameon": True,
            "legend.fancybox": False,
            "legend.edgecolor": "0.35",
            "legend.framealpha": 1.0,
            "legend.borderpad": 0.4,
            "legend.handlelength": 1.6,
            "mathtext.fontset": "stix",
            "lines.linewidth": 1.8,
            "lines.markersize": 8.5,
            "errorbar.capsize": 4.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.dpi": SAVE_DPI,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def new_figure():
    apply_academic_style()
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt.subplots(figsize=FIGURE_SIZE, layout="constrained")


def style_axes(ax, xlabel: str, ylabel: str) -> None:
    ax.set_xlabel(xlabel, labelpad=10)
    ax.set_ylabel(ylabel, labelpad=10)
    ax.xaxis.label.set_clip_on(False)
    ax.yaxis.label.set_clip_on(False)
    ax.grid(False)
    ax.tick_params(axis="both", which="major", direction="out", top=False, right=False)
    ax.minorticks_off()
    for spine in ax.spines.values():
        spine.set_color("black")
        spine.set_linewidth(matplotlib.rcParams["axes.linewidth"])


def apply_sci_axis(ax, axis: str = "y") -> None:
    ax.ticklabel_format(axis=axis, style="sci", scilimits=(-2, 4), useMathText=True)
    offset = ax.yaxis.get_offset_text() if axis == "y" else ax.xaxis.get_offset_text()
    offset.set_fontsize(FONT_SIZE)
    offset.set_fontfamily("serif")


def _to_axes(ax, x: float, y: float) -> tuple[float, float]:
    display = ax.transData.transform((x, y))
    axes_xy = ax.transAxes.inverted().transform(display)
    return float(axes_xy[0]), float(axes_xy[1])


def _occupancy(ax):
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    points: list[tuple[float, float]] = []
    boxes: list[tuple[float, float, float, float]] = []

    def add_point(x: float, y: float) -> None:
        if xlim[0] <= x <= xlim[1] and ylim[0] <= y <= ylim[1]:
            points.append(_to_axes(ax, x, y))

    for line in ax.lines:
        xs, ys = line.get_data()
        n = min(len(xs), len(ys))
        if n == 0:
            continue
        if n == 2 and (xs[0] == xs[1] or ys[0] == ys[1]):
            continue
        for x, y in zip(xs, ys):
            add_point(float(x), float(y))

    for patch in ax.patches:
        if not patch.get_fill():
            continue
        bb = patch.get_window_extent().transformed(ax.transAxes.inverted())
        boxes.append((bb.x0, bb.y0, bb.x1, bb.y1))

    for collection in ax.collections:
        if isinstance(collection, LineCollection):
            continue
        if isinstance(collection, PathCollection):
            offsets = collection.get_offsets()
            if getattr(offsets, "size", 0):
                for x, y in offsets:
                    add_point(float(x), float(y))

    return points, boxes


def _hits(bbox, points, boxes) -> int:
    x0, x1 = bbox.x0 - _LEGEND_PAD, bbox.x1 + _LEGEND_PAD
    y0, y1 = bbox.y0 - _LEGEND_PAD, bbox.y1 + _LEGEND_PAD
    n = sum(1 for px, py in points if x0 <= px <= x1 and y0 <= py <= y1)
    for bx0, by0, bx1, by1 in boxes:
        if x0 <= bx1 and x1 >= bx0 and y0 <= by1 and y1 >= by0:
            n += 999
    return n


_INSIDE = dict(frameon=True, borderaxespad=0.35, labelspacing=0.25, framealpha=0.92, ncol=1)


def legend_corner(ax) -> str | None:
    handles, labels = ax.get_legend_handles_labels()
    if not any(labels):
        return None
    fig = ax.figure
    fig.canvas.draw()
    points, boxes = _occupancy(ax)
    scored: list[tuple[int, str]] = []
    for loc in _CORNERS:
        legend = ax.legend(handles, labels, loc=loc, **_INSIDE)
        legend.set_in_layout(False)
        fig.canvas.draw()
        bbox = legend.get_window_extent().transformed(ax.transAxes.inverted())
        legend.remove()
        spills = bbox.x0 < 0.0 or bbox.y0 < 0.0 or bbox.x1 > 1.0 or bbox.y1 > 1.0
        scored.append((10_000 if spills else _hits(bbox, points, boxes), loc))
    scored.sort(key=lambda item: (item[0], _CORNERS.index(item[1])))
    hits, loc = scored[0]
    return loc if hits <= _HITS_MAX else None


def place_legend_below(ax, ncol: int = 1):
    handles, labels = ax.get_legend_handles_labels()
    if not any(labels):
        return None
    loc = legend_corner(ax)
    if loc is not None:
        legend = ax.legend(handles, labels, loc=loc, **_INSIDE)
        legend.set_in_layout(False)
        legend.set_zorder(20)
        return legend
    return ax.figure.legend(handles, labels, loc="outside lower center", ncol=ncol)


def save_figure(fig, path: Path) -> None:
    apply_academic_style()
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=SAVE_DPI, bbox_inches="tight", pad_inches=0.12, facecolor="white")
    plt.close(fig)
    print(f"wrote {path}")


