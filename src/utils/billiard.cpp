#include "billiard.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

#include "cell_grid.hpp"
#include "dump.hpp"
#include "geometry.hpp"

namespace {

bool repulsion_on_i(double xi, double yi, double ri, double xj, double yj, double rj, double &fx, double &fy) {
	const double dx = xj - xi;
	const double dy = yj - yi;
	const double sum = ri + rj;
	if (!in_contact(dx, dy, sum))
		return false;
	const double dist = std::sqrt(dx * dx + dy * dy);
	if (!(dist > 0.0))
		throw std::runtime_error("coincident centers: the contact normal is undefined");
	const double scale = -spring_k * (sum - dist) / dist;
	fx = scale * dx;
	fy = scale * dy;
	return true;
}

void contact_forces(const std::vector<Particle> &particles, const std::vector<Obstacle> &obstacles, double R,
                    CellGrid &grid, std::vector<double> &fx, std::vector<double> &fy) {
	const int count = static_cast<int>(particles.size());
	std::fill(fx.begin(), fx.end(), 0.0);
	std::fill(fy.begin(), fy.end(), 0.0);
	grid.clear();
	for (int i = 0; i < count; ++i)
		grid.insert(i, particles[i].x + R, particles[i].y + R);

	for (int i = 0; i < count; ++i) {
		const Particle &pi = particles[i];
		const int cx = grid.cell_coord(pi.x + R);
		const int cy = grid.cell_coord(pi.y + R);
		for (int oy = -1; oy <= 1; ++oy) {
			for (int ox = -1; ox <= 1; ++ox) {
				const int nx = cx + ox, ny = cy + oy;
				if (nx < 0 || nx >= grid.cells_per_side() || ny < 0 || ny >= grid.cells_per_side())
					continue;
				for (int j : grid.cell(grid.cell_index(nx, ny))) {
					if (j <= i)
						continue;
					double fij_x = 0.0, fij_y = 0.0;
					if (!repulsion_on_i(pi.x, pi.y, pi.r, particles[j].x, particles[j].y, particles[j].r, fij_x,
					                    fij_y))
						continue;
					fx[static_cast<std::size_t>(i)] += fij_x;
					fy[static_cast<std::size_t>(i)] += fij_y;
					fx[static_cast<std::size_t>(j)] -= fij_x;
					fy[static_cast<std::size_t>(j)] -= fij_y;
				}
			}
		}

		for (const Obstacle &o : obstacles) {
			double fox = 0.0, foy = 0.0;
			if (!repulsion_on_i(pi.x, pi.y, pi.r, o.x, o.y, o.radius, fox, foy))
				continue;
			fx[static_cast<std::size_t>(i)] += fox;
			fy[static_cast<std::size_t>(i)] += foy;
		}

		const double dist = std::sqrt(pi.x * pi.x + pi.y * pi.y);
		if (!(dist > R - pi.r))
			continue;
		double fwx = 0.0, fwy = 0.0;
		if (!repulsion_on_i(pi.x, pi.y, pi.r, (R + pi.r) * pi.x / dist, (R + pi.r) * pi.y / dist, pi.r, fwx, fwy))
			continue;
		fx[static_cast<std::size_t>(i)] += fwx;
		fy[static_cast<std::size_t>(i)] += fwy;
	}
}

void mark_obstacle_contacts(std::vector<Particle> &particles, const std::vector<Obstacle> &obstacles) {
	for (Particle &p : particles) {
		if (p.used)
			continue;
		for (const Obstacle &o : obstacles) {
			if (!in_contact(p.x - o.x, p.y - o.y, p.r + o.radius))
				continue;
			p.used = 1;
			break;
		}
	}
}

void validate_run(const std::vector<Particle> &particles, const std::vector<Obstacle> &obstacles,
                  const BilliardRun &run) {
	if (!std::isfinite(run.R) || !(run.R > 0.0))
		throw std::invalid_argument("R must be finite and > 0");
	if (!std::isfinite(run.dt) || !(run.dt > 0.0))
		throw std::invalid_argument("dt must be finite and > 0");
	if (!std::isfinite(run.tf) || !(run.tf > 0.0))
		throw std::invalid_argument("tf must be finite and > 0");
	if (run.n < 1)
		throw std::invalid_argument("n must be >= 1");
	const double ratio = run.tf / run.dt;
	if (!std::isfinite(ratio) || ratio > 1.0e12)
		throw std::invalid_argument("tf/dt is too large");
	if (particles.empty())
		throw std::invalid_argument("N must be >= 1");
	if (particles.size() > static_cast<std::size_t>(std::numeric_limits<int>::max()))
		throw std::invalid_argument("N does not fit in an int");

	const double r = particles[0].r;
	const double m = particles[0].m;
	if (!std::isfinite(r) || !(r > 0.0) || !(r <= run.R))
		throw std::invalid_argument("r must be finite and in (0, R]");
	if (!std::isfinite(m) || !(m > 0.0))
		throw std::invalid_argument("m must be finite and > 0");
	for (const Particle &p : particles) {
		if (!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.vx) || !std::isfinite(p.vy))
			throw std::invalid_argument("particle state must be finite");
		if (!(p.r == r) || !(p.m == m))
			throw std::invalid_argument("all particles must share r and m");
	}
	validate_obstacles(obstacles, run.R, r);
}

}

void integrate_billiard(std::vector<Particle> &particles, const std::vector<Obstacle> &obstacles,
                        const BilliardRun &run, std::ostream *out) {
	validate_run(particles, obstacles, run);

	const int count = static_cast<int>(particles.size());
	const double side = 2.0 * run.R;
	CellGrid grid(side, cells_per_side_for(side, 2.0 * particles[0].r));
	std::vector<double> fx(particles.size()), fy(particles.size());
	std::vector<double> prev_x(particles.size()), prev_y(particles.size());
	std::vector<double> next_x(particles.size()), next_y(particles.size());

	contact_forces(particles, obstacles, run.R, grid, fx, fy);
	const double dt = run.dt;
	const double half_dt2 = 0.5 * dt * dt;
	for (int i = 0; i < count; ++i) {
		const std::size_t index = static_cast<std::size_t>(i);
		const double inv_m = 1.0 / particles[index].m;
		prev_x[index] = particles[index].x - dt * particles[index].vx + half_dt2 * fx[index] * inv_m;
		prev_y[index] = particles[index].y - dt * particles[index].vy + half_dt2 * fy[index] * inv_m;
	}

	const double dt2 = dt * dt;
	const long long nsteps = std::llround(run.tf / dt);
	for (long long step = 0; step <= nsteps; ++step) {
		contact_forces(particles, obstacles, run.R, grid, fx, fy);
		mark_obstacle_contacts(particles, obstacles);
		for (int i = 0; i < count; ++i) {
			const std::size_t index = static_cast<std::size_t>(i);
			const double inv_m = 1.0 / particles[index].m;
			next_x[index] = 2.0 * particles[index].x - prev_x[index] + dt2 * fx[index] * inv_m;
			next_y[index] = 2.0 * particles[index].y - prev_y[index] + dt2 * fy[index] * inv_m;
			if (!std::isfinite(next_x[index]) || !std::isfinite(next_y[index]))
				throw std::runtime_error("non-finite position; the contact force diverged");
			particles[index].vx = (next_x[index] - prev_x[index]) / (2.0 * dt);
			particles[index].vy = (next_y[index] - prev_y[index]) / (2.0 * dt);
		}
		if (out != nullptr && step % run.n == 0) {
			write_dump_frame(*out, static_cast<double>(step) * dt, particles);
			if (out->fail())
				throw std::runtime_error("error writing the trajectory");
		}
		if (step == nsteps)
			break;
		for (int i = 0; i < count; ++i) {
			const std::size_t index = static_cast<std::size_t>(i);
			prev_x[index] = particles[index].x;
			prev_y[index] = particles[index].y;
			particles[index].x = next_x[index];
			particles[index].y = next_y[index];
		}
	}
}
