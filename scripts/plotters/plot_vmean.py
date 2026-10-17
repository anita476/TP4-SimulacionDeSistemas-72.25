import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import FONT_SIZE, SERIES, new_figure, save_figure, style_axes


def load_curve(path: Path) -> tuple[list[float], list[float], list[float]]:
    times: list[float] = []
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
                if header[:3] != ["t", "vmean_mean", "vmean_std"]:
                    raise ValueError(f"{path}: expected columns t vmean_mean vmean_std")
                continue
            if len(parts) < 3:
                raise ValueError(f"{path}: expected 't mean std', got {line!r}")
            times.append(float(parts[0]))
            means.append(float(parts[1]))
            stds.append(float(parts[2]))
    if len(times) < 3:
        raise ValueError(f"{path}: need at least 3 rows")
    return times, means, stds


def main() -> None:
    parser = argparse.ArgumentParser(description="2.3: mean speed <v>(t), mu +- sigma over seeds, log time axis")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--v0", type=float, required=True, help="initial speed (m/s): draws the MB 2D plateau sqrt(pi/4) v0")
    parser.add_argument("--t-fit", type=float, default=None, help="instant used for the fit, marked on the curve")
    args = parser.parse_args()
    try:
        times, means, stds = load_curve(args.input)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    # t = 0 cannot be shown on a log axis; it is the delta at v0, i.e. <v> = v0 (the top of the y range).
    positive = [(t, m, s) for t, m, s in zip(times, means, stds) if t > 0.0]
    if not positive:
        parser.error(f"{args.input}: no t > 0 rows")
    t_pos = [row[0] for row in positive]
    m_pos = [row[1] for row in positive]
    s_pos = [row[2] for row in positive]
    plateau = math.sqrt(math.pi / 4.0) * args.v0

    fig, ax = new_figure()
    ax.fill_between(
        t_pos,
        [m - s for m, s in zip(m_pos, s_pos)],
        [m + s for m, s in zip(m_pos, s_pos)],
        color=SERIES[0],
        alpha=0.25,
        linewidth=0,
        zorder=2,
        label=r"$\mu \pm \sigma$ sobre realizaciones",
    )
    ax.plot(t_pos, m_pos, color=SERIES[0], linewidth=2.0, zorder=3, label=r"$\langle v \rangle(t)$")
    ax.axhline(
        plateau,
        color="black",
        linestyle="--",
        linewidth=1.4,
        zorder=1,
        label=rf"MB 2D: $\sqrt{{\pi/4}}\,v_0 = {plateau:.3f}$ m/s",
    )
    if args.t_fit is not None:
        i_fit = min(range(len(t_pos)), key=lambda i: abs(t_pos[i] - args.t_fit))
        ax.plot(
            [t_pos[i_fit]],
            [m_pos[i_fit]],
            linestyle="none",
            marker="o",
            markersize=9,
            color=SERIES[1],
            markeredgecolor="black",
            markeredgewidth=0.6,
            zorder=4,
            label=rf"ajuste: $t = {t_pos[i_fit]:g}$ s",
        )
    ax.set_xscale("log")
    style_axes(ax, r"tiempo $t$ (s)", r"$\langle v \rangle$ (m/s)")
    ax.set_xlim(min(t_pos), max(t_pos) * 1.25)  # room for the marker at the last frame
    lo = min(m - s for m, s in zip(m_pos, s_pos))
    hi = max(max(m + s for m, s in zip(m_pos, s_pos)), args.v0)
    pad = 0.06 * (hi - lo)
    ax.set_ylim(lo - pad, hi + pad)
    ax.legend(loc="upper right", ncol=1, frameon=True, framealpha=0.92, borderaxespad=0.5, fontsize=FONT_SIZE - 4)
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()
