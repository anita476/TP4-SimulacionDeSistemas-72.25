#pragma once

#include <iosfwd>
#include <vector>

#include "obstacle.hpp"
#include "particle.hpp"

struct BilliardRun {
	double R;
	double dt;
	double tf;
	int n;
};

void integrate_billiard(std::vector<Particle> &particles, const std::vector<Obstacle> &obstacles,
                        const BilliardRun &run, std::ostream *out);
