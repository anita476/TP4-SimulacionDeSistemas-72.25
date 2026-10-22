#pragma once

// single particle oscillator
struct ParticleOscillator {
  double gamma; // coeficiente de amortiguamiento
  double k;     // coef de elasticidad
  // f = m a = -k r - gamma v

  double m; // particle mass (partícula puntual)
  double vx;
  double vx_old;

  double r; // current position
  double r_old;

  // for beeman:
  double a_current;
  double a_old;
};