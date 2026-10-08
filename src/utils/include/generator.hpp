#pragma once

#include <cstdint>
#include <vector>

#include "obstacle.hpp"
#include "particle.hpp"

struct GeneratorConfig {
	int N = 100;
	double R = 0.51;
	double r = 0.0175, m = 0.025, v0 = 1.0;
	std::vector<Obstacle> obstacles;
	std::uint64_t seed = 0;
	int max_attempts = 100000;
};

struct GeneratorStats {
	double packing_fraction = 0.0;
};

std::vector<Particle> generate_particles(const GeneratorConfig &cfg, GeneratorStats *stats = nullptr);
