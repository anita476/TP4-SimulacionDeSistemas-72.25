#pragma once

#include <string>
#include <vector>

struct Obstacle {
	double x, y, radius;
};

void validate_obstacles(const std::vector<Obstacle> &obstacles, double R, double particle_radius);

std::vector<Obstacle> load_obstacles(const std::string &path, double R, double particle_radius);
