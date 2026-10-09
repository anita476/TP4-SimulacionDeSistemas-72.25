#pragma once

// single particle oscillator
struct ParticleOscillator {
  double gamma; // coeficiente de amortiguamiento
  double k;     // coef de elasticidad
  // f = ma = k * r  - gamma *v

  double m; // particle mass  -> es puntual así que radio 0
  double vx;
  double vx_old;

  double r; // current position
  double r_old;

  // for beeman:
  double a_current;
  double a_old;
};