import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import SERIES, new_figure, place_legend_below, save_figure, style_axes


def load_curve(path: Path) -> tuple[list[float], list[float]]:
    kbts: list[float] = []
    errors: list[float] = []
    header = None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if header is None:
                header = parts
                if header[:2] != ["kBT", "E"]:
                    raise ValueError(f"{path}: expected columns kBT E")
                continue
            if len(parts) < 2:
                raise ValueError(f"{path}: expected 'kBT E', got {line!r}")
            kbts.append(float(parts[0]))
            errors.append(float(parts[1]))
    if len(kbts) < 3:
        raise ValueError(f"{path}: need at least 3 rows")
    return kbts, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="2.3: fit error E(kBT) of the Maxwell-Boltzmann sweep")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", type=float, default=None, help="kBT (J) to mark, e.g. m v0^2/2")
    args = parser.parse_args()
    try:
        kbts, errors = load_curve(args.input)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    i_min = min(range(len(errors)), key=lambda i: errors[i])
    fig, ax = new_figure()
    ax.plot(kbts, errors, color=SERIES[0], linewidth=2.0, zorder=3, label=r"$E(k_B T)$")
    ax.plot(
        [kbts[i_min]],
        [errors[i_min]],
        linestyle="none",
        marker="o",
        markersize=9,
        color=SERIES[1],
        markeredgecolor="black",
        markeredgewidth=0.6,
        zorder=4,
        label=rf"mínimo: $k_B T^* = {kbts[i_min]:.4g}\,\mathrm{{J}}$",
    )
    if args.reference is not None:
        ax.axvline(
            args.reference,
            color="black",
            linestyle=":",
            zorder=2,
            label=rf"$m v_0^2/2 = {args.reference:.4g}\,\mathrm{{J}}$",
        )
    style_axes(ax, r"energía térmica $k_B T$ (J)", r"error $E(k_B T)$ (s$^2$/m$^2$)")
    ax.set_xlim(min(kbts), max(kbts))
    ax.set_ylim(0, max(errors) * 1.08)
    place_legend_below(ax, ncol=2)
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()