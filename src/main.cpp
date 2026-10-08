#include <argparse/argparse.hpp>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "dump.hpp"
#include "generator.hpp"
#include "obstacle.hpp"

namespace {

std::ofstream open_dump(const std::string &path) {
	const std::filesystem::path parent = std::filesystem::path(path).parent_path();
	if (!parent.empty())
		std::filesystem::create_directories(parent);
	std::ofstream file(path);
	if (!file)
		throw std::runtime_error("could not open " + path);
	file << std::setprecision(12);
	return file;
}

}

int main(int argc, char *argv[]) {
	argparse::ArgumentParser program("TimeDriven-TP4", "0.1", argparse::default_arguments::help);

	program.add_argument("-R").default_value(0.51).scan<'g', double>().help("domain radius (m)");
	program.add_argument("-N").default_value(100).scan<'i', int>().help("particle count");
	program.add_argument("-r").default_value(0.0175).scan<'g', double>().help("particle radius (m)");
	program.add_argument("-m").default_value(0.025).scan<'g', double>().help("particle mass (kg)");
	program.add_argument("-v0").default_value(1.0).scan<'g', double>().help("initial speed (m/s)");
	program.add_argument("-seed").default_value(0).scan<'i', int>().help("RNG seed (0 = unfixed)");
	program.add_argument("-obstacles")
	    .default_value(std::string(""))
	    .help("obstacle file: one 'x y radius' line per obstacle (m)");
	program.add_argument("-xo").scan<'g', double>().help(
	    "two obstacles of radius r at (-xo, 0) and (+xo, 0); not combined with -obstacles");
	program.add_argument("--out").default_value(std::string("")).help("dump path (empty = no dump)");

	try {
		program.parse_args(argc, argv);
	} catch (const std::exception &err) {
		std::cerr << err.what() << '\n';
		std::cerr << program;
		return 1;
	}

	const double R = program.get<double>("-R");
	const int N = program.get<int>("-N");
	const double r = program.get<double>("-r");
	const double m = program.get<double>("-m");
	const double v0 = program.get<double>("-v0");
	const int seed = program.get<int>("-seed");
	const std::string obstacles_path = program.get<std::string>("-obstacles");
	const std::string out_path = program.get<std::string>("--out");
	const bool use_xo = program.is_used("-xo");

	try {
		if (use_xo && !obstacles_path.empty())
			throw std::invalid_argument("-xo and -obstacles cannot be combined");

		std::vector<Obstacle> obstacles;
		if (use_xo) {
			const double xo = program.get<double>("-xo");
			if (!(xo >= 0.0))
				throw std::invalid_argument("-xo must be >= 0");
			obstacles = {{-xo, 0.0, r}, {xo, 0.0, r}};
			validate_obstacles(obstacles, R, r);
		} else if (!obstacles_path.empty()) {
			obstacles = load_obstacles(obstacles_path, R, r);
		}

		GeneratorConfig gen;
		gen.N = N;
		gen.R = R;
		gen.r = r;
		gen.m = m;
		gen.v0 = v0;
		gen.obstacles = obstacles;
		gen.seed = static_cast<std::uint64_t>(seed);

		GeneratorStats gen_stats;
		const std::vector<Particle> particles = generate_particles(gen, &gen_stats);

		if (!out_path.empty()) {
			std::ofstream file = open_dump(out_path);
			write_dump_header(file, R, r, m, N, obstacles);
			write_dump_frame(file, 0.0, particles);
		}

		std::cout << std::fixed << std::setprecision(6) << "Particles:       " << N << '\n'
		          << "Domain radius:   " << R << " m\n"
		          << "Obstacles:       " << obstacles.size() << '\n'
		          << "Random seed:     " << seed << (seed == 0 ? " (unfixed)\n" : "\n") << std::setprecision(2)
		          << "Occupied area:   " << 100.0 * gen_stats.packing_fraction << "%\n";
		if (out_path.empty())
			std::cout << "Trajectory file: disabled\n";
		else
			std::cout << "Trajectory file: " << out_path << '\n';
	} catch (const std::exception &err) {
		std::cerr << "error: " << err.what() << '\n';
		return 1;
	}
	return 0;
}
