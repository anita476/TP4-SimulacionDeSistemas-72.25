#pragma once

struct Particle {
	double x, y, r, vx, vy;
	double m = 0.0;
	int used = 0;
};
