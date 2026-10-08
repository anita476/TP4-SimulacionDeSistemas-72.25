#include "obstacle.hpp"

#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "geometry.hpp"

namespace {

std::vector<Obstacle> read_obstacles(const std::string &path) {
	std::ifstream in(path);
	if (!in)
		throw std::runtime_error("could not open " + path);

	std::vector<Obstacle> obstacles;
	std::string line;
	int lineno = 0;
	while (std::getline(in, line)) {
		++lineno;
		const std::size_t hash = line.find('#');
		if (hash != std::string::npos)
			line.erase(hash);

		std::istringstream fields(line);
		std::vector<std::string> tokens;
		for (std::string tok; fields >> tok;)
			tokens.push_back(tok);
		if (tokens.empty())
			continue;

		const std::string where = path + ":" + std::to_string(lineno);
		if (tokens.size() != 3)
			throw std::runtime_error(where + ": expected 3 fields x y radius, got " + std::to_string(tokens.size()));
		auto to_double = [&where](const std::string &tok) {
			std::size_t pos = 0;
			double v = 0.0;
			try {
				v = std::stod(tok, &pos);
			} catch (const std::logic_error &) {
				throw std::runtime_error(where + ": not a numeric field '" + tok + "'");
			}
			if (pos != tok.size())
				throw std::runtime_error(where + ": not a numeric field '" + tok + "'");
			return v;
		};
		obstacles.push_back({to_double(tokens[0]), to_double(tokens[1]), to_double(tokens[2])});
	}
	if (in.bad())
		throw std::runtime_error("error reading " + path);

	return obstacles;
}

}

void validate_obstacles(const std::vector<Obstacle> &obstacles, double R, double r) {
	if (!std::isfinite(R) || R <= 0.0 || !std::isfinite(r) || r <= 0.0) {
		throw std::invalid_argument("obstacle validation: R and particle radius must be finite and positive");
	}
	for (std::size_t k = 0; k < obstacles.size(); ++k) {
		const Obstacle &o = obstacles[k];
		const std::string where = "obstacle " + std::to_string(k + 1);
		if (!std::isfinite(o.x) || !std::isfinite(o.y) || !std::isfinite(o.radius)) {
			throw std::invalid_argument(where + ": coordinates and radius must be finite");
		}
		if (o.radius < r)
			throw std::runtime_error(where + ": radius < r");
		if (!disc_inside_circle(o.x, o.y, o.radius, R))
			throw std::runtime_error(where + ": not inside the circle");

		for (std::size_t j = 0; j < k; ++j) {
			if (in_contact(o.x - obstacles[j].x, o.y - obstacles[j].y, o.radius + obstacles[j].radius))
				throw std::runtime_error(where + " overlaps obstacle " + std::to_string(j + 1));
		}
	}
}

std::vector<Obstacle> load_obstacles(const std::string &path, double R, double particle_radius) {
	auto obstacles = read_obstacles(path);
	validate_obstacles(obstacles, R, particle_radius);
	return obstacles;
}
