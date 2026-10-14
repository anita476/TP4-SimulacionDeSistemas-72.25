#include <argparse/argparse.hpp>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

#include "integrators.hpp"

int main(int argc, char *argv[]) {
	argparse::ArgumentParser program("Oscillator-TP4", "0.1", argparse::default_arguments::help);

	program.add_argument("-method")
	    .default_value(std::string("velocity_verlet"))
	    .choices("euler_pc", "verlet", "verlet_lagged", "velocity_verlet", "beeman")
	    .help("integration scheme");
	program.add_argument("-dt").required().scan<'g', double>().help("time step (s)");
	program.add_argument("-tf").default_value(5.0).scan<'g', double>().help("final time (s)");
	program.add_argument("-m").default_value(70.0).scan<'g', double>().help("mass (kg)");
	program.add_argument("-k").default_value(1.0e4).scan<'g', double>().help("spring constant (N/m)");
	program.add_argument("-gamma").default_value(100.0).scan<'g', double>().help("damping (kg/s)");
	program.add_argument("-A").default_value(1.0).scan<'g', double>().help("amplitude r(0) (m)");
	program.add_argument("--out").default_value(std::string("")).help("trajectory 't x_num x_an' (empty = none)");

	try {
		program.parse_args(argc, argv);
	} catch (const std::exception &err) {
		std::cerr << err.what() << '\n';
		std::cerr << program;
		return 1;
	}

	try {
		Oscillator osc;
		osc.m = program.get<double>("-m");
		osc.k = program.get<double>("-k");
		osc.gamma = program.get<double>("-gamma");
		osc.A = program.get<double>("-A");
		const OscillatorRun run{parse_method(program.get<std::string>("-method")), program.get<double>("-dt"),
		                        program.get<double>("-tf")};
		const std::string out_path = program.get<std::string>("--out");

		std::ofstream file;
		if (!out_path.empty()) {
			const std::filesystem::path parent = std::filesystem::path(out_path).parent_path();
			if (!parent.empty())
				std::filesystem::create_directories(parent);
			file.open(out_path);
			if (!file)
				throw std::runtime_error("could not open " + out_path);
			file << std::setprecision(17);
		}

		const double ecm = integrate_oscillator(osc, run, out_path.empty() ? nullptr : &file);
		if (!std::isfinite(ecm))
			throw std::runtime_error("ECM is not finite");
		if (!out_path.empty() && file.fail())
			throw std::runtime_error("error writing " + out_path);

		std::cout << std::setprecision(17) << "method " << method_name(run.method) << '\n'
		          << "dt " << run.dt << '\n'
		          << "tf " << run.tf << '\n'
		          << "steps " << std::llround(run.tf / run.dt) << '\n'
		          << "ecm " << ecm << '\n';
	} catch (const std::exception &err) {
		std::cerr << "error: " << err.what() << '\n';
		return 1;
	}
	return 0;
}