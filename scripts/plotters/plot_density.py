import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import MARKERS, SERIES, new_figure, place_legend_below, save_figure, style_axes


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


def main() -> None:
    parser = argparse.ArgumentParser(description="2.4a: mean t90 and t100 vs packing fraction")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--series", nargs=2, action="append", metavar=("LABEL", "TABLE"), required=True)
    parser.add_argument("--xlabel", default=r"densidad $\phi$")
    parser.add_argument("--ylabel", default="tiempo (s)")
    parser.add_argument("--ymax", type=float, default=None)
    args = parser.parse_args()
    if args.ymax is not None and not (args.ymax > 0.0):
        parser.error("--ymax must be > 0")

    fig, ax = new_figure()
    ymax = 0.0
    try:
        for i, (label, table) in enumerate(args.series):
            rows = load_table(Path(table), ("phi", "t_mean", "t_std"))
            xs, means, stds = [], [], []
            for row in rows:
                mean = float(row["t_mean"])
                std = float(row["t_std"])
                if math.isnan(mean) or math.isnan(std):
                    continue
                xs.append(float(row["phi"]))
                means.append(mean)
                stds.append(std)
            if not xs:
                parser.error(f"{table}: no finite rows")
            order = sorted(range(len(xs)), key=lambda j: xs[j])
            xs = [xs[j] for j in order]
            means = [means[j] for j in order]
            stds = [stds[j] for j in order]
            color = SERIES[i % len(SERIES)]
            marker = MARKERS[i % len(MARKERS)]
            ax.errorbar(
                xs,
                means,
                yerr=stds,
                color=color,
                marker=marker,
                markeredgecolor="black",
                markeredgewidth=0.6,
                linestyle="-",
                zorder=3,
                label=label,
            )
            ymax = max(ymax, max(mean + std for mean, std in zip(means, stds)))
    except (OSError, ValueError) as error:
        parser.error(str(error))

    style_axes(ax, args.xlabel, args.ylabel)
    ax.set_ylim(0, args.ymax if args.ymax is not None else (ymax * 1.08 if ymax > 0 else 1.0))
    place_legend_below(ax, ncol=min(len(args.series), 2))
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()
