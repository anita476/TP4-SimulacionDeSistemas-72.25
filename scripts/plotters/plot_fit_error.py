import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import FIGURE_SIZE, SERIES, new_figure, save_figure, style_axes


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
    parser.add_argument("--kinetic", type=float, default=None, help="kBT (J) measured as m <v^2>/2")
    args = parser.parse_args()
    try:
        kbts, errors = load_curve(args.input)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    i_min = min(range(len(errors)), key=lambda i: errors[i])
    fig, ax = new_figure()
    fig.set_size_inches(1.3 * FIGURE_SIZE[0], 1.3 * FIGURE_SIZE[1])
    top = max(errors) * 1.08
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
        label=rf"$k_B T^* = {kbts[i_min]:.4g}\,\mathrm{{J}}$",
    )
    if args.reference is not None:
        ax.vlines(
            args.reference,
            0.0,
            top,
            color="black",
            linestyle=":",
            zorder=2,
            label=rf"$m v_0^2/2 = {args.reference:.4g}\,\mathrm{{J}}$",
        )
    if args.kinetic is not None:
        ax.vlines(
            args.kinetic,
            0.0,
            top,
            color="black",
            linestyle="-.",
            zorder=2,
            label=rf"$m \langle v^2 \rangle/2 = {args.kinetic:.4g}\,\mathrm{{J}}$",
        )
    style_axes(ax, r"energía térmica $k_B T$ (J)", r"error $E(k_B T)$ (s$^2$/m$^2$)")
    ax.set_xlim(min(kbts), max(kbts))
    ax.set_ylim(0, top)
    ax.legend(loc="upper right", ncol=1, frameon=True, framealpha=0.92, borderaxespad=0.5)
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()