from dataclasses import dataclass
from pathlib import Path


@dataclass
class Frame:
    t: float
    nu: int
    particles: list[tuple[float, float, float, float, int]]


@dataclass
class Traj:
    R: float
    r: float
    N: int
    obstacles: list[tuple[float, float, float]]
    frames: list[Frame]
    m: float | None = None
    k: float | None = None


def _fail(path: str, lineno: int, msg: str) -> None:
    raise ValueError(f"{path}:{lineno}: {msg}")


def _tokens(path: str, lineno: int, line: str, expected: int) -> list[str]:
    parts = line.split()
    if len(parts) != expected:
        _fail(path, lineno, f"expected {expected} fields, got {len(parts)}: {line!r}")
    return parts


def _used(path: str, lineno: int, token: str) -> int:
    if token == "azul":
        return 0
    if token == "roja":
        return 1
    _fail(path, lineno, f"color must be azul or roja, not {token!r}")
    return 0


def read_traj(path: str | Path) -> Traj:
    path_s = str(path)
    rows: list[tuple[int, str]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.split("#", 1)[0].strip()
            if line:
                rows.append((lineno, line))
    if not rows:
        raise ValueError(f"{path_s}: empty file")

    header: dict[str, float] = {}
    N: int | None = None
    obstacles: list[tuple[float, float, float]] = []
    i = 0
    while i < len(rows) and rows[i][1].split()[0] != "t":
        lineno, line = rows[i]
        tag = line.split()[0]
        if tag in ("R", "r", "m", "k"):
            header[tag] = float(_tokens(path_s, lineno, line, 2)[1])
        elif tag == "N":
            N = int(_tokens(path_s, lineno, line, 2)[1])
        elif tag == "O":
            _, x, y, radius = _tokens(path_s, lineno, line, 4)
            obstacles.append((float(x), float(y), float(radius)))
        else:
            _fail(path_s, lineno, f"unknown header tag {tag!r}")
        i += 1

    missing = [key for key in ("R", "r") if key not in header]
    if "m" in header and header["m"] <= 0:
        raise ValueError(f"{path_s}: m must be > 0, got {header['m']}")
    if "k" in header and header["k"] <= 0:
        raise ValueError(f"{path_s}: k must be > 0, got {header['k']}")
    if N is None:
        missing.append("N")
    if missing:
        raise ValueError(f"{path_s}: missing header fields: {', '.join(missing)}")
    assert N is not None
    for key in ("R", "r"):
        if header[key] <= 0:
            raise ValueError(f"{path_s}: {key} must be > 0, got {header[key]}")
    if N < 1:
        raise ValueError(f"{path_s}: N must be >= 1, got {N}")

    frames: list[Frame] = []
    while i < len(rows):
        lineno, line = rows[i]
        parts = _tokens(path_s, lineno, line, 4)
        if parts[0] != "t" or parts[2] != "Nu":
            _fail(path_s, lineno, f"expected 't <s> Nu <int>', got {line!r}")
        t, nu = float(parts[1]), int(parts[3])
        i += 1
        if i + N > len(rows):
            raise ValueError(f"{path_s}: truncated frame at t={t}")
        particles: list[tuple[float, float, float, float, int]] = []
        for _ in range(N):
            lineno, line = rows[i]
            x, y, vx, vy, color = _tokens(path_s, lineno, line, 5)
            used = _used(path_s, lineno, color)
            particles.append((float(x), float(y), float(vx), float(vy), used))
            i += 1
        used_count = sum(p[4] for p in particles)
        if used_count != nu:
            _fail(path_s, lineno, f"Nu={nu} but {used_count} particles are used")
        frames.append(Frame(t, nu, particles))

    if not frames:
        raise ValueError(f"{path_s}: no frames")

    return Traj(
        R=header["R"],
        r=header["r"],
        N=N,
        obstacles=obstacles,
        frames=frames,
        m=header.get("m"),
        k=header.get("k"),
    )


def read_nu_series(path: str | Path) -> tuple[int, list[tuple[float, int]]]:
    path_s = str(path)
    N: int | None = None
    frames: list[tuple[float, int]] = []
    in_header = True
    lineno = 0
    with open(path, encoding="utf-8") as fh:
        while True:
            raw = fh.readline()
            if not raw:
                break
            lineno += 1
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if in_header:
                tag = line.split()[0]
                if tag == "t":
                    if N is None:
                        raise ValueError(f"{path_s}: missing header field N")
                    in_header = False
                elif tag == "N":
                    N = int(_tokens(path_s, lineno, line, 2)[1])
                    if N < 1:
                        raise ValueError(f"{path_s}: N must be >= 1, got {N}")
                    continue
                elif tag in ("R", "r", "m", "k"):
                    _tokens(path_s, lineno, line, 2)
                    continue
                elif tag == "O":
                    _tokens(path_s, lineno, line, 4)
                    continue
                else:
                    _fail(path_s, lineno, f"unknown header tag {tag!r}")
            if not in_header:
                parts = _tokens(path_s, lineno, line, 4)
                if parts[0] != "t" or parts[2] != "Nu":
                    _fail(path_s, lineno, f"expected 't <s> Nu <int>', got {line!r}")
                t, nu = float(parts[1]), int(parts[3])
                if not (0 <= nu <= N):
                    _fail(path_s, lineno, f"Nu={nu} is outside [0, {N}]")
                skipped = 0
                while skipped < N:
                    particle = fh.readline()
                    if not particle:
                        raise ValueError(f"{path_s}: truncated frame at t={t}")
                    lineno += 1
                    if not particle.split("#", 1)[0].strip():
                        continue
                    skipped += 1
                frames.append((t, nu))
    if N is None:
        raise ValueError(f"{path_s}: missing header field N")
    if not frames:
        raise ValueError(f"{path_s}: no frames")
    return N, frames
