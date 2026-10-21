import argparse
from decimal import Decimal, InvalidOperation
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from metrics import mean_std, trajectory_ecm
from plot_style import new_figure, save_figure, style_axes, viridis_colors

METHODS = {
    "euler_pc": "Euler predictor-corrector",
    "verlet": "Verlet",
    "velocity_verlet": "Velocity Verlet",
    "beeman": "Beeman",
    "velocity_verlet_vanilla": "Velocity Verlet Vanilla"
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Mean oscillator ECM vs dt for each integration method")
    parser.add_argument("--input_dir", type=Path, required=True, help="run_12.py output directory")
    parser.add_argument("--output", type=Path, required=True, help="output plot path")
    for method in METHODS:
        parser.add_argument(f"--{method}", action="store_true", help=f"include {METHODS[method]} in the plot")
    args = parser.parse_args()
    selected_methods = [method for method in METHODS if getattr(args, method)]
    if not selected_methods:
        selected_methods = list(METHODS)

    if not args.input_dir.is_dir():
        parser.error(f"input directory does not exist: {args.input_dir}")

    errors: dict[str, dict[Decimal, list[float]]] = {method: {} for method in selected_methods}
    try:
        for method in selected_methods:
            method_dir = args.input_dir / method
            if not method_dir.is_dir():
                continue
            for trajectory in sorted(method_dir.glob("*.txt")):
                prefix = f"{method}_"
                if not trajectory.name.startswith(prefix) or trajectory.stem.endswith("_analitica"):
                    continue
                dt_text, separator, run_text = trajectory.stem[len(prefix):].rpartition("_")
                if not separator or not run_text.isdigit():
                    continue
                try:
                    dt = Decimal(dt_text)
                except InvalidOperation:
                    raise ValueError(f"{trajectory}: invalid dt in filename") from None
                if not dt.is_finite() or dt <= 0:
                    raise ValueError(f"{trajectory}: dt must be finite and > 0")

                analytic = trajectory.with_name(f"{trajectory.stem}_analitica{trajectory.suffix}")
                ecm = trajectory_ecm(trajectory, analytic)
                errors[method].setdefault(dt, []).append(ecm)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print("dt\tmethod\tecm_mean")
    for dt in sorted({dt for series in errors.values() for dt in series}):
        for method in selected_methods:
            series = errors[method]
            if dt in series:
                ecm_mean, _ecm_std = mean_std(series[dt])
                print(f"{dt}\t{method}\t{ecm_mean:.10g}")

    fig, ax = new_figure()
    colors = viridis_colors(len(METHODS))
    plotted = False
    for index, (method, label) in enumerate(METHODS.items()):
        if method not in selected_methods:
            continue
        series = errors[method]
        if not series:
            continue
        points = sorted((float(dt), *mean_std(values)) for dt, values in series.items())
        dts = [dt for dt, _mean, _std in points]
        means = [mean for _dt, mean, _std in points]
        stds = [std for _dt, _mean, std in points]
        if (
            any(not math.isfinite(dt) or dt <= 0 for dt in dts)
            or any(not math.isfinite(mean) or mean <= 0 for mean in means)
            or any(not math.isfinite(std) or std < 0 for std in stds)
        ):
            parser.error(f"{method}: dt, mean ECM and standard deviation must be finite and valid for logarithmic axes")
        lower = [mean - std if mean > std else math.nan for mean, std in zip(means, stds)]
        upper = [mean + std for mean, std in zip(means, stds)]
        ax.fill_between(dts, lower, upper, color=colors[index], alpha=0.18, linewidth=0, zorder=2)
        ax.plot(
            dts,
            means,
            color=colors[index],
            marker={"beeman": "^", "velocity_verlet": "D"}.get(method, "o"),
            markersize=8,
            markeredgecolor="black",
            markeredgewidth=0.6,
            alpha=1,
            linestyle="--" if method == "beeman" else "-",
            label=label,
            zorder=3,
        )
        plotted = True

    if not plotted:
        parser.error(f"no run_12.py trajectory files found under {args.input_dir}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    style_axes(ax, r"$dt$ (s)", r"ECM ($\mathrm{m}^2$)")
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower center", ncol=2)
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()