import math

from traj import Frame, Traj


def _overlap_energy(k: float, overlap: float) -> float:
    if overlap <= 0.0:
        return 0.0
    return 0.5 * k * overlap * overlap


def total_energy(traj: Traj, frame: Frame) -> float:
    if traj.m is None or traj.k is None:
        raise ValueError("m and k are required to compute the energy")
    kinetic = 0.0
    potential = 0.0
    particles = frame.particles
    for x, y, vx, vy, _used in particles:
        kinetic += 0.5 * traj.m * (vx * vx + vy * vy)
    for i, (xi, yi, _vxi, _vyi, _usedi) in enumerate(particles):
        for xj, yj, _vxj, _vyj, _usedj in particles[i + 1 :]:
            dist = math.hypot(xj - xi, yj - yi)
            if dist == 0.0:
                raise ValueError("coincident centers: the contact potential is undefined")
            potential += _overlap_energy(traj.k, 2.0 * traj.r - dist)
        for ox, oy, radius in traj.obstacles:
            dist = math.hypot(ox - xi, oy - yi)
            if dist == 0.0:
                raise ValueError("coincident centers: the contact potential is undefined")
            potential += _overlap_energy(traj.k, traj.r + radius - dist)
        dist = math.hypot(xi, yi)
        potential += _overlap_energy(traj.k, dist - (traj.R - traj.r))
    return kinetic + potential


def energy_series(traj: Traj) -> list[tuple[float, float]]:
    return [(frame.t, total_energy(traj, frame)) for frame in traj.frames]


def max_relative_drift(traj: Traj) -> float:
    energies = [total_energy(traj, frame) for frame in traj.frames]
    e0 = energies[0]
    if e0 == 0.0:
        raise ValueError("E(0) is 0; the relative energy drift is undefined")
    return max(abs(energy - e0) / abs(e0) for energy in energies)
