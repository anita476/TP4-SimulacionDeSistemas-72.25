#pragma once

#include <iosfwd>
#include <vector>

#include "obstacle.hpp"
#include "particle.hpp"

constexpr double spring_k = 1.0e4;

struct BilliardRun {
	double R;
	double dt;
	double tf;
	int n;
};

void integrate_billiard(std::vector<Particle> &particles, const std::vector<Obstacle> &obstacles,
                        const BilliardRun &run, std::ostream *out);
