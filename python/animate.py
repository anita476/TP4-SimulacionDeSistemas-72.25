import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

import matplotlib
from matplotlib.patches import Circle

from plot_style import BLUE, FONT_SIZE, SAVE_DPI, VERMILLION, apply_academic_style, legend_corner, style_axes
from traj import Frame, Traj, read_traj

FRESH = BLUE
USED = VERMILLION
OBSTACLE = "#4d4d4d"
GIF_DPI = 100
MP4_DPI = 120
ARROW_SCALE = 0.06


def _stats_line(frame: Frame, n: int) -> str:
    return rf"$N_u = {frame.nu}$    $F_u = {frame.nu / n:.2f}$"


def make_figure(traj: Traj, arrows: bool = False):
    apply_academic_style()
    import matplotlib.pyplot as plt

    R, r, n = traj.R, traj.r, traj.n
    margin = max(0.08 * R, 2.0 * r)
    fig = plt.figure(figsize=(8.0, 8.6))
    ax = fig.add_axes([0.14, 0.16, 0.78, 0.74])
    ax.set_xlim(-R - margin, R + margin)
    ax.set_ylim(-R - margin, R + margin)
    ax.set_aspect("equal")
    style_axes(ax, r"posición $x$ (m)", r"posición $y$ (m)")

    ax.add_patch(Circle((0.0, 0.0), R, fill=False, edgecolor="black", lw=1.4, zorder=5))
    for x, y, radius in traj.obstacles:
        ax.add_patch(Circle((x, y), radius, fc=OBSTACLE, ec="black", lw=0.6, zorder=2))

    patches = []
    for x, y, _vx, _vy, used in traj.frames[0].particles:
        patch = Circle((x, y), r, fc=USED if used else FRESH, ec="black", lw=0.4, zorder=4)
        ax.add_patch(patch)
        patches.append(patch)

    quiver = None
    if arrows:
        xs = [p[0] for p in traj.frames[0].particles]
        ys = [p[1] for p in traj.frames[0].particles]
        us = [p[2] for p in traj.frames[0].particles]
        vs = [p[3] for p in traj.frames[0].particles]
        quiver = ax.quiver(
            xs,
            ys,
            us,
            vs,
            angles="xy",
            scale_units="xy",
            scale=1.0 / ARROW_SCALE,
            color="black",
            width=0.003,
            zorder=5,
        )

    ax.plot([], [], linestyle="none", marker="o", color=FRESH, markeredgecolor="black", label="fresca")
    ax.plot([], [], linestyle="none", marker="o", color=USED, markeredgecolor="black", label="usada")
    if traj.obstacles:
        ax.plot([], [], linestyle="none", marker="o", color=OBSTACLE, markeredgecolor="black", label="obstáculo")
    step = max(1, len(traj.frames) // 200)
    probe = ax.scatter(
        [p[0] for f in traj.frames[::step] for p in f.particles],
        [p[1] for f in traj.frames[::step] for p in f.particles],
        s=0,
        alpha=0.0,
    )
    corner = legend_corner(ax)
    probe.remove()
    handles, labels = ax.get_legend_handles_labels()
    ncol = 3 if traj.obstacles else 2
    if corner is not None:
        legend = ax.legend(handles, labels, loc=corner, frameon=True, framealpha=0.92, fancybox=False)
        legend.set_zorder(20)
    else:
        ax.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
            ncol=ncol,
            frameon=True,
            fancybox=False,
        )

    stats = fig.text(0.5, 0.975, _stats_line(traj.frames[0], n), ha="center", va="top", fontsize=FONT_SIZE)

    def draw(index: int) -> None:
        frame = traj.frames[index]
        for patch, particle in zip(patches, frame.particles):
            x, y, _vx, _vy, used = particle
            patch.center = (x, y)
            patch.set_facecolor(USED if used else FRESH)
        if quiver is not None:
            quiver.set_offsets([(p[0], p[1]) for p in frame.particles])
            quiver.set_UVC([p[2] for p in frame.particles], [p[3] for p in frame.particles])
        stats.set_text(_stats_line(frame, n))

    draw(0)
    return fig, draw


def main() -> None:
    parser = argparse.ArgumentParser(description="Animate a circular-billiard dump")
    parser.add_argument("--traj", required=True, help="dump written by the engine (--out)")
    parser.add_argument("--out", help="output GIF")
    parser.add_argument("--mp4", help="output MP4 (requires ffmpeg)")
    parser.add_argument("--png", help="PNG of one frame")
    parser.add_argument("--frame", type=int, default=None, help="PNG frame index (default: middle; 0 = initial)")
    parser.add_argument("--show", action="store_true", help="open a window")
    parser.add_argument("--fps", type=int, default=8, help="dump frames per second of video")
    parser.add_argument("--arrows", action="store_true", help="velocity arrows")
    args = parser.parse_args()

    if args.fps < 1:
        sys.exit("--fps must be >= 1")
    if not args.out and not args.mp4 and not args.png and not args.show:
        args.show = True
    if not args.show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter

    try:
        traj = read_traj(args.traj)
    except (OSError, ValueError) as error:
        sys.exit(str(error))
    fig, draw = make_figure(traj, arrows=args.arrows)
    n_frames = len(traj.frames)

    def play(index: int) -> None:
        draw(index)

    if args.png:
        index = n_frames // 2 if args.frame is None else args.frame
        if not 0 <= index < n_frames:
            sys.exit(f"--frame must be in [0, {n_frames - 1}]")
        draw(index)
        png_path = Path(args.png)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_path, dpi=SAVE_DPI, facecolor="white")
        print(f"wrote {png_path} (frame {index})")

    if args.out:
        gif_path = Path(args.out)
        gif_path.parent.mkdir(parents=True, exist_ok=True)
        anim = FuncAnimation(fig, play, frames=n_frames, blit=False, interval=1000 / args.fps)
        anim.save(gif_path, writer=PillowWriter(fps=args.fps), dpi=GIF_DPI, savefig_kwargs={"facecolor": "white"})
        print(f"wrote {gif_path} ({n_frames} frames at {args.fps} fps)")

    if args.mp4:
        mp4_path = Path(args.mp4)
        mp4_path.parent.mkdir(parents=True, exist_ok=True)
        anim = FuncAnimation(fig, play, frames=n_frames, blit=False, interval=1000 / args.fps)
        anim.save(
            mp4_path,
            writer=FFMpegWriter(fps=args.fps, bitrate=3000),
            dpi=MP4_DPI,
            savefig_kwargs={"facecolor": "white"},
        )
        print(f"wrote {mp4_path} ({n_frames} frames at {args.fps} fps)")

    if args.show:
        FuncAnimation(fig, play, frames=n_frames, blit=False, interval=1000 / args.fps, repeat=True)
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
