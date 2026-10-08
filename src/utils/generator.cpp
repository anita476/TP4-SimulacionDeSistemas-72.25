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
constexpr double kMinSpacing = 1.0 + 1e-9;

struct Site {
	double x, y;
};

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

std::vector<Site> hex_sites(double a, double R, double r, const std::vector<Obstacle> &obstacles) {
	std::vector<Site> sites;
	const double h = a * std::sqrt(3.0) / 2.0;
	const double reach = R - r;
	const int j_max = static_cast<int>(std::ceil(reach / h)) + 1;
	const int i_max = static_cast<int>(std::ceil(reach / a)) + 1;
	for (int j = -j_max; j <= j_max; ++j) {
		const double y = static_cast<double>(j) * h;
		const double offset = (j & 1) ? 0.5 * a : 0.0;
		for (int i = -i_max; i <= i_max; ++i) {
			const double x = offset + static_cast<double>(i) * a;
			if (!disc_inside_circle(x, y, r, R) || overlaps_obstacle(x, y, r, obstacles))
				continue;
			sites.push_back({x, y});
		}
	}
	return sites;
}

std::vector<Site> hex_positions(int N, double R, double r, const std::vector<Obstacle> &obstacles) {
	const std::vector<Site> tight = hex_sites(kMinSpacing * 2.0 * r, R, r, obstacles);
	const int capacity = static_cast<int>(tight.size());
	if (N > capacity) {
		std::ostringstream msg;
		msg << "the hexagonal lattice admits at most " << capacity << " particles in this disk; input: " << N;
		throw std::runtime_error(msg.str());
	}
	double lo = kMinSpacing * 2.0 * r, hi = 2.0 * R;
	for (int it = 0; it < 100; ++it) {
		const double mid = 0.5 * (lo + hi);
		if (static_cast<int>(hex_sites(mid, R, r, obstacles).size()) >= N)
			lo = mid;
		else
			hi = mid;
	}
	const std::vector<Site> all = hex_sites(lo, R, r, obstacles);
	const long long M = static_cast<long long>(all.size());
	std::vector<Site> chosen;
	chosen.reserve(static_cast<std::size_t>(N));
	for (long long i = 0; i < N; ++i)
		chosen.push_back(all[static_cast<std::size_t>((2 * i * M + N) / (2LL * N))]);
	return chosen;
}

}

double packing_fraction(const GeneratorConfig &cfg) {
	validate(cfg);
	return occupied_fraction(cfg.R, cfg.r, cfg.N, cfg.obstacles);
}

std::vector<Particle> generate_particles(const GeneratorConfig &cfg) {
	validate(cfg);

	std::mt19937_64 rng;
	if (cfg.seed == 0) {
		std::random_device rd;
		rng.seed(rd());
	} else {
		rng.seed(cfg.seed);
	}
	std::uniform_real_distribution<double> unit(0.0, 1.0);
	std::uniform_real_distribution<double> angle(0.0, 2.0 * kPi);

	if (cfg.placement == Placement::Hex) {
		const std::vector<Site> sites = hex_positions(cfg.N, cfg.R, cfg.r, cfg.obstacles);
		std::vector<Particle> particles;
		particles.reserve(sites.size());
		for (const Site &site : sites) {
			const double theta = angle(rng);
			particles.push_back(
			    Particle{site.x, site.y, cfg.r, cfg.v0 * std::cos(theta), cfg.v0 * std::sin(theta), cfg.m});
		}
		return particles;
	}

	const double side = 2.0 * cfg.R;
	CellGrid grid(side, cells_per_side_for(side, 2.0 * cfg.r));
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
