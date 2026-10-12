import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import MARKERS, SERIES, new_figure, place_legend_below, save_figure, style_axes
from speed import mb_pdf


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
    parser = argparse.ArgumentParser(description="2.3: speed PDF f(v) at selected times")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--series", nargs=2, action="append", metavar=("LABEL", "TABLE"), required=True)
    parser.add_argument("--fit", type=float, default=None, help="kBT (J) for the 2D Maxwell-Boltzmann overlay")
    parser.add_argument("--m", type=float, default=None, help="particle mass (kg); required with --fit")
    parser.add_argument("--vline", nargs=2, action="append", metavar=("V", "LABEL"), help="vertical line at speed V")
    parser.add_argument("--xmax", type=float, default=None, help="upper x limit (m/s)")
    args = parser.parse_args()
    if args.xmax is not None and not (args.xmax > 0.0):
        parser.error("--xmax must be > 0")
    if args.fit is not None:
        if args.m is None or not (args.m > 0.0):
            parser.error("--m > 0 is required with --fit")
        if not (args.fit > 0.0):
            parser.error("--fit must be > 0")
    elif args.m is not None:
        parser.error("--m is only used with --fit")

    fig, ax = new_figure()
    vmax = 0.0
    fmax = 0.0
    try:
        for i, (label, table) in enumerate(args.series):
            rows = load_table(Path(table), ("v", "f_mean", "f_std"))
            vs = [float(row["v"]) for row in rows]
            means = [float(row["f_mean"]) for row in rows]
            stds = [float(row["f_std"]) for row in rows]
            order = sorted(range(len(vs)), key=lambda j: vs[j])
            vs = [vs[j] for j in order]
            means = [means[j] for j in order]
            stds = [stds[j] for j in order]
            color = SERIES[i % len(SERIES)]
            marker = MARKERS[i % len(MARKERS)]
            ax.errorbar(
                vs,
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
            vmax = max(vmax, max(vs) if vs else 0.0)
            fmax = max(fmax, max(mean + std for mean, std in zip(means, stds)))
        if args.vline:
            for v_text, label in args.vline:
                v = float(v_text)
                if not (v >= 0.0):
                    parser.error("--vline speed must be >= 0")
                ax.axvline(v, color="black", linestyle=":", zorder=2, label=label)
                vmax = max(vmax, v)
        if args.fit is not None:
            assert args.m is not None
            n = 400
            curve_v = [vmax * i / n for i in range(n + 1)]
            curve_f = [mb_pdf(v, args.m, args.fit) for v in curve_v]
            ax.plot(
                curve_v,
                curve_f,
                color="black",
                linestyle="--",
                zorder=4,
                label=rf"$k_B T = {args.fit:.4g}\,\mathrm{{J}}$",
            )
            fmax = max(fmax, max(curve_f) if curve_f else 0.0)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    style_axes(ax, r"módulo de la velocidad $v$ (m/s)", r"$f(v)$ (s/m)")
    x_right = args.xmax if args.xmax is not None else (vmax * 1.02 if vmax > 0 else 1.0)
    ax.set_xlim(0, x_right)
    ax.set_ylim(0, fmax * 1.08 if fmax > 0 else 1.0)
    extra = (1 if args.fit is not None else 0) + (len(args.vline) if args.vline else 0)
    place_legend_below(ax, ncol=min(len(args.series) + extra, 3))
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()
