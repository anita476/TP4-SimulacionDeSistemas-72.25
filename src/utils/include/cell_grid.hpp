#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <vector>

inline int cells_per_side_for(double side, double contact_diameter) {
	return std::max(1, static_cast<int>(std::floor(side / contact_diameter)));
}

class CellGrid {
public:
	CellGrid(double side, int cells_per_side)
	    : side_(side), cells_per_side_(cells_per_side),
	      cells_(static_cast<std::size_t>(cells_per_side) * static_cast<std::size_t>(cells_per_side)) {}

	int cells_per_side() const { return cells_per_side_; }

	int cell_coord(double shifted) const {
		if (!std::isfinite(shifted) || shifted < 0.0 || shifted > side_) {
			throw std::runtime_error("coordinate " + std::to_string(shifted) + " is outside the indexing square [0, " +
			                         std::to_string(side_) + "]");
		}
		const int c = static_cast<int>(shifted * static_cast<double>(cells_per_side_) / side_);
		if (c == cells_per_side_)
			return cells_per_side_ - 1;
		if (c < 0 || c >= cells_per_side_)
			throw std::runtime_error("cell index is outside the grid");
		return c;
	}

	int cell_index(int cx, int cy) const { return cy * cells_per_side_ + cx; }

	void insert(int id, double shifted_x, double shifted_y) {
		cells_[static_cast<std::size_t>(cell_index(cell_coord(shifted_x), cell_coord(shifted_y)))].push_back(id);
	}

	void clear() {
		for (std::vector<int> &ids : cells_)
			ids.clear();
	}

	const std::vector<int> &cell(int index) const { return cells_[static_cast<std::size_t>(index)]; }

private:
	double side_;
	int cells_per_side_;
	std::vector<std::vector<int>> cells_;
};
