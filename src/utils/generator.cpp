#include "generator.hpp"

#include <algorithm>
#include <cmath>
#include <random>
#include <sstream>
#include <stdexcept>
#include <vector>

#include "geometry.hpp"

namespace {
constexpr double kPi = 3.14159265358979323846;

class CellGrid {
public:
	CellGrid(double side, int cells_per_side)
	    : side_(side), cells_per_side_(cells_per_side),
	      cells_(static_cast<std::size_t>(cells_per_side) * static_cast<std::size_t>(cells_per_side)) {}

	int cells_per_side() const { return cells_per_side_; }

	int cell_coord(double shifted) const {
		const int c = static_cast<int>(shifted * cells_per_side_ / side_);
		if (c < 0)
			return 0;
		if (c >= cells_per_side_)
			return cells_per_side_ - 1;
		return c;
	}

	int cell_index(int cx, int cy) const { return cy * cells_per_side_ + cx; }

	void insert(int id, double shifted_x, double shifted_y) {
		cells_[cell_index(cell_coord(shifted_x), cell_coord(shifted_y))].push_back(id);
	}

	const std::vector<int> &cell(int index) const { return cells_[index]; }

private:
	double side_;
	int cells_per_side_;
	std::vector<std::vector<int>> cells_;
};

void validate(const GeneratorConfig &cfg) {
	if (cfg.N < 1)
		throw std::invalid_argument("N must be >= 1");
	if (cfg.R <= 0.0 || cfg.r <= 0.0 || cfg.m <= 0.0)
		throw std::invalid_argument("R, r and m must be positive");
	if (cfg.R < cfg.r)
		throw std::invalid_argument("the domain is smaller than the particle");
	if (cfg.max_attempts < 1)
		throw std::invalid_argument("max_attempts must be >= 1");
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

std::vector<Particle> generate_particles(const GeneratorConfig &cfg, GeneratorStats *stats) {
	validate(cfg);

	const double side = 2.0 * cfg.R;
	const int cells_per_side = std::max(1, static_cast<int>(std::floor(side / (2.0 * cfg.r))));
	CellGrid grid(side, cells_per_side);

	std::mt19937_64 rng;
	if (cfg.seed == 0) {
		std::random_device rd;
		rng.seed(rd());
	} else {
		rng.seed(cfg.seed);
	}
	std::uniform_real_distribution<double> unit(0.0, 1.0);
	std::uniform_real_distribution<double> angle(0.0, 2.0 * kPi);

	double obstacle_area = 0.0;
	for (const Obstacle &o : cfg.obstacles)
		obstacle_area += kPi * o.radius * o.radius;

	const double disc_area = kPi * cfg.r * cfg.r;
	const double domain_area = kPi * cfg.R * cfg.R;
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
			    << " attempts (occupied fraction " << (obstacle_area + i * disc_area) / domain_area
			    << "): lower N, shrink the obstacles, or raise max_attempts";
			throw std::runtime_error(msg.str());
		}
	}

	if (stats != nullptr)
		stats->packing_fraction = (obstacle_area + cfg.N * disc_area) / domain_area;
	return particles;
}
