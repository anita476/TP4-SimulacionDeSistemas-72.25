#include "integrators.hpp"

#include <cmath>
#include <ostream>
#include <stdexcept>
#include <string>

#include "methods.hpp"

Method parse_method(const std::string &name) {
	if (name == "euler_pc")
		return Method::EulerPC;
	if (name == "verlet")
		return Method::Verlet;
	if (name == "velocity_verlet")
		return Method::VelocityVerlet;
	if (name == "beeman")
		return Method::Beeman;
	throw std::invalid_argument("unknown method '" + name +
	                            "' (expected euler_pc, verlet, velocity_verlet or beeman)");
}

const char *method_name(Method method) {
	switch (method) {
	case Method::EulerPC:
		return "euler_pc";
	case Method::Verlet:
		return "verlet";
	case Method::VelocityVerlet:
		return "velocity_verlet";
	case Method::Beeman:
		return "beeman";
	}
	return "?";
}

double Oscillator::omega() const { return std::sqrt(k / m - gamma * gamma / (4.0 * m * m)); }

double Oscillator::analytic(double t) const { return A * std::exp(-gamma * t / (2.0 * m)) * std::cos(omega() * t); }

namespace {

integrators::Step step_for(Method method) {
	switch (method) {
	case Method::EulerPC:
		return &integrators::euler_predictor_corrector::oscillator_step;
	case Method::Verlet:
		return &integrators::verlet::oscillator_step;
	case Method::VelocityVerlet:
		return &integrators::velocity_verlet::oscillator_step;
	case Method::Beeman:
		return &integrators::beeman::oscillator_step;
	}
	throw std::invalid_argument("unknown method");
}

ParticleOscillator initial_state(const Oscillator &osc, double dt) {
	ParticleOscillator p{};
	p.gamma = osc.gamma;
	p.k = osc.k;
	p.m = osc.m;
	p.r = osc.x0();
	p.vx = osc.v0();
	const double a0 = osc.acceleration(p.r, p.vx);
	p.r_old = p.r - p.vx * dt + 0.5 * a0 * dt * dt;
	p.vx_old = p.vx - a0 * dt;
	p.a_current = a0;
	p.a_old = osc.acceleration(p.r_old, p.vx_old);
	return p;
}

void validate(const Oscillator &osc, const OscillatorRun &run) {
	if (!std::isfinite(osc.m) || !(osc.m > 0.0))
		throw std::invalid_argument("m must be finite and > 0");
	if (!std::isfinite(osc.k) || !(osc.k > 0.0))
		throw std::invalid_argument("k must be finite and > 0");
	if (!std::isfinite(osc.gamma) || !(osc.gamma >= 0.0))
		throw std::invalid_argument("gamma must be finite and >= 0");
	if (!std::isfinite(osc.A))
		throw std::invalid_argument("A must be finite");
	if (!(osc.k / osc.m > osc.gamma * osc.gamma / (4.0 * osc.m * osc.m)))
		throw std::invalid_argument("overdamped: the analytic solution of slide 37 needs k/m > gamma^2/(4 m^2)");
	if (!std::isfinite(run.dt) || !(run.dt > 0.0))
		throw std::invalid_argument("dt must be finite and > 0");
	if (!std::isfinite(run.tf) || !(run.tf > 0.0))
		throw std::invalid_argument("tf must be finite and > 0");
	if (run.tf / run.dt > 1.0e9)
		throw std::invalid_argument("tf/dt is too large");
}

} // namespace

double integrate_oscillator(const Oscillator &osc, const OscillatorRun &run, std::ostream *out) {
	validate(osc, run);
	const double dt = run.dt;
	const long long nsteps = std::llround(run.tf / dt);
	const integrators::Step step = step_for(run.method);

	ParticleOscillator p = initial_state(osc, dt);
	double sum = 0.0;
	for (long long n = 0; n <= nsteps; ++n) {
		const double t = static_cast<double>(n) * dt;
		const double x_an = osc.analytic(t);
		const double e = p.r - x_an;
		sum += e * e;
		if (!std::isfinite(p.r) || !std::isfinite(sum))
			throw std::runtime_error("the integration diverged (dt too large for " + std::string(method_name(run.method)) +
			                         ")");
		if (out != nullptr) {
			*out << t << ' ' << p.r << ' ' << x_an << '\n';
			if (out->fail())
				throw std::runtime_error("error writing the trajectory");
		}
		if (n == nsteps)
			break;
		step(p, dt);
	}
	return sum / static_cast<double>(nsteps + 1);
}