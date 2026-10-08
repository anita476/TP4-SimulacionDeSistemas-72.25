#include "generator.hpp"

#include <cmath>
#include <random>
#include <sstream>
#include <stdexcept>
#include <vector>

#include "cell_grid.hpp"
#include "geometry.hpp"

namespace {
constexpr double kPi = 3.14159265358979323846;

void validate(const GeneratorConfig &cfg) {
	if (cfg.N < 1)
		throw std::invalid_argument("N must be >= 1");
	if (!std::isfinite(cfg.R) || !std::isfinite(cfg.r) || !std::isfinite(cfg.m) || !(cfg.R > 0.0) || !(cfg.r > 0.0) ||
	    !(cfg.m > 0.0))
		throw std::invalid_argument("R, r and m must be finite and positive");
	if (!std::isfinite(cfg.v0))
		throw std::invalid_argument("v0 must be finite");
	if (cfg.R < cfg.r)
		throw std::invalid_argument("the domain is smaller than the particle");
	if (cfg.max_attempts < 1)
		throw std::invalid_argument("max_attempts must be >= 1");
}

double occupied_fraction(double R, double r, int count, const std::vector<Obstacle> &obstacles) {
	double obstacle_area = 0.0;
	for (const Obstacle &o : obstacles)
		obstacle_area += kPi * o.radius * o.radius;
	return (obstacle_area + count * kPi * r * r) / (kPi * R * R);
}

bool overlaps_placed(double x, double y, double r, const std::vector<Particle> &placed, const CellGrid &grid,
                     double R) {
	const int cx = grid.cell_coord(x + R);
	const int cy = grid.cell_coord(y + R);
	for (int dy = -1; dy <= 1; ++dy) {
		for (int dx = -1; dx <= 1; ++dx) {
			const int nx = cx + dx, ny = cy + dy;
			if (nx < 0 || nx >= grid.cells_per_side() || ny < 0 || ny >= grid.cells_per_side())
				continue;
			for (int j : grid.cell(grid.cell_index(nx, ny))) {
				if (in_contact(x - placed[j].x, y - placed[j].y, r + placed[j].r))
					return true;
			}
		}
	}
	return false;
}

bool overlaps_obstacle(double x, double y, double r, const std::vector<Obstacle> &obstacles) {
	for (const Obstacle &o : obstacles)
		if (in_contact(x - o.x, y - o.y, r + o.radius))
			return true;
	return false;
}

}

double packing_fraction(const GeneratorConfig &cfg) {
	validate(cfg);
	return occupied_fraction(cfg.R, cfg.r, cfg.N, cfg.obstacles);
}

std::vector<Particle> generate_particles(const GeneratorConfig &cfg) {
	validate(cfg);

	const double side = 2.0 * cfg.R;
	CellGrid grid(side, cells_per_side_for(side, 2.0 * cfg.r));

	std::mt19937_64 rng;
	if (cfg.seed == 0) {
		std::random_device rd;
		rng.seed(rd());
	} else {
		rng.seed(cfg.seed);
	}
	std::uniform_real_distribution<double> unit(0.0, 1.0);
	std::uniform_real_distribution<double> angle(0.0, 2.0 * kPi);

	const double reach = cfg.R - cfg.r;

	std::vector<Particle> particles;
	particles.reserve(static_cast<std::size_t>(cfg.N));

	for (int i = 0; i < cfg.N; ++i) {
		bool placed = false;
		for (int attempt = 0; attempt < cfg.max_attempts && !placed; ++attempt) {
			const double rho = reach * std::sqrt(unit(rng));
			const double phi = angle(rng);
			const double x = rho * std::cos(phi);
			const double y = rho * std::sin(phi);
			if (overlaps_obstacle(x, y, cfg.r, cfg.obstacles) || overlaps_placed(x, y, cfg.r, particles, grid, cfg.R))
				continue;

			grid.insert(i, x + cfg.R, y + cfg.R);
			const double theta = angle(rng);
			particles.push_back(Particle{x, y, cfg.r, cfg.v0 * std::cos(theta), cfg.v0 * std::sin(theta), cfg.m});
			placed = true;
		}

		if (!placed) {
			std::ostringstream msg;
			msg << "could not place particle " << i + 1 << " of " << cfg.N << " after " << cfg.max_attempts
			    << " attempts (occupied fraction " << occupied_fraction(cfg.R, cfg.r, i, cfg.obstacles)
			    << "): lower N, shrink the obstacles, or raise max_attempts";
			throw std::runtime_error(msg.str());
		}
	}

	return particles;
}
