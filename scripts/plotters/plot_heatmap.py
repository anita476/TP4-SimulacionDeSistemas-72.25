import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import matplotlib
import numpy as np

from plot_style import FONT_SIZE, apply_academic_style, new_figure, save_figure, style_axes


def load_table(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header = None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if header is None:
                header = parts
                missing = [key for key in required if key not in header]
                if missing:
                    raise ValueError(f"{path}: expected columns {' '.join(required)}")
                continue
            raw = dict(zip(header, parts))
            missing = [key for key in required if not raw.get(key)]
            if missing:
                raise ValueError(f"{path}: missing {', '.join(missing)}")
            rows.append({key: raw[key] for key in required})
    if not rows:
        raise ValueError(f"{path}: no data rows")
    return rows


def _edges(values: np.ndarray) -> np.ndarray:
    if len(values) == 1:
        pad = 0.5 if values[0] == 0 else abs(values[0]) * 0.05
        return np.array([values[0] - pad, values[0] + pad])
    deltas = np.diff(values)
    return np.concatenate(([values[0] - deltas[0] / 2.0], values[:-1] + deltas / 2.0, [values[-1] + deltas[-1] / 2.0]))


def main() -> None:
    parser = argparse.ArgumentParser(description="2.4b: heatmap of mean t90 vs xo and N")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-row", action="store_true", help="divide each row by its minimum")
    args = parser.parse_args()

    try:
        rows = load_table(args.input, ("N", "xo", "t90_mean", "n_reached", "n_total"))
    except (OSError, ValueError) as error:
        parser.error(str(error))

    ns = sorted({int(row["N"]) for row in rows})
    xos = sorted({float(row["xo"]) for row in rows})
    grid = {(int(row["N"]), float(row["xo"])): row for row in rows}
    data = np.full((len(ns), len(xos)), np.nan)
    for j, n in enumerate(ns):
        for i, xo in enumerate(xos):
            row = grid.get((n, xo))
            if row is None:
                continue
            if int(row["n_reached"]) != int(row["n_total"]):
                continue
            value = float(row["t90_mean"])
            if math.isnan(value):
                continue
            data[j, i] = value
    if not np.isfinite(data).any():
        parser.error(f"{args.input}: no complete t90 cells")
    if args.per_row:
        for j in range(data.shape[0]):
            finite_row = data[j, np.isfinite(data[j])]
            if finite_row.size == 0:
                continue
            baseline = float(finite_row.min())
            if not (baseline > 0.0):
                parser.error(f"N={ns[j]}: row minimum must be > 0 to normalize")
            data[j] = data[j] / baseline

    fig, ax = new_figure()
    cmap = matplotlib.colormaps["YlOrRd"].copy()
    cmap.set_bad("#f0f0f0")
    finite = data[np.isfinite(data)]
    mesh = ax.pcolormesh(
        _edges(np.array(xos)),
        np.arange(len(ns) + 1) - 0.5,
        data,
        cmap=cmap,
        vmin=float(finite.min()),
        vmax=float(finite.max()),
        shading="flat",
        zorder=2,
    )
    for j in range(len(ns)):
        row = data[j]
        if not np.isfinite(row).any():
            continue
        i = int(np.nanargmin(row))
        ax.plot(xos[i], j, marker="o", markersize=9, color="white", markeredgecolor="black", markeredgewidth=0.8, zorder=4)
    style_axes(ax, r"posición $x_o$ (m)", r"cantidad de partículas $N$")
    ax.set_yticks(range(len(ns)))
    ax.set_yticklabels([str(n) for n in ns])
    ax.set_xlim(_edges(np.array(xos))[0], _edges(np.array(xos))[-1])
    ax.set_ylim(-0.5, len(ns) - 0.5)
    cbar = fig.colorbar(mesh, ax=ax, pad=0.03)
    if args.per_row:
        cbar.set_label(r"$\langle t_{90}\rangle / \min\langle t_{90}\rangle$", size=FONT_SIZE)
    else:
        cbar.set_label(r"tiempo $\langle t_{90}\rangle$ (s)", size=FONT_SIZE)
    cbar.ax.tick_params(labelsize=FONT_SIZE)
    cbar.outline.set_linewidth(1.15)
    save_figure(fig, args.output)


if __name__ == "__main__":
    apply_academic_style()
    main()
