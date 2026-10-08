#pragma once

inline bool in_contact(double dx, double dy, double sum_radii) {
	return dx * dx + dy * dy < sum_radii * sum_radii;
}

inline bool disc_inside_circle(double x, double y, double radius, double R) {
	if (!(radius <= R))
		return false;
	const double limit = R - radius;
	return x * x + y * y <= limit * limit;
}
