#pragma once

#include <ostream>
#include <vector>

#include "obstacle.hpp"
#include "particle.hpp"

inline void write_dump_header(std::ostream &out, double R, double r, double m, int N,
                              const std::vector<Obstacle> &obstacles) {
	out << "R " << R << '\n';
	out << "r " << r << '\n';
	out << "m " << m << '\n';
	out << "N " << N << '\n';
	for (const Obstacle &o : obstacles)
		out << "O " << o.x << ' ' << o.y << ' ' << o.radius << '\n';
}

inline void write_dump_frame(std::ostream &out, double t, const std::vector<Particle> &particles) {
	int nu = 0;
	for (const Particle &p : particles)
		nu += p.used ? 1 : 0;
	out << "t " << t << " Nu " << nu << '\n';
	for (const Particle &p : particles)
		out << p.x << ' ' << p.y << ' ' << p.vx << ' ' << p.vy << ' ' << (p.used ? "roja" : "azul") << '\n';
}
