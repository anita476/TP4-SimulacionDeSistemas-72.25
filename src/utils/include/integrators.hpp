#pragma once

#include <iosfwd>
#include <string>

enum class Method {
  EulerPC,
  Verlet,
  VelocityVerlet,
  Beeman,
  VelocityVerletVanilla
};

Method parse_method(const std::string &name);
const char *method_name(Method method);

struct Oscillator {
  double m = 70.0;
  double k = 1.0e4;
  double gamma = 100.0;
  double A = 1.0;

  double acceleration(double x, double v) const {
    return (-k * x - gamma * v) / m;
  }
  double omega() const;
  double analytic(double t) const;
  double x0() const { return A; }
  double v0() const { return -A * gamma / (2.0 * m); }
};

struct OscillatorRun {
  Method method;
  double dt;
  double tf;
};

void integrate_oscillator(const Oscillator &osc, const OscillatorRun &run,
                          std::ostream *out,
                          std::ostream *analytic_out = nullptr);