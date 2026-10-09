#include "methods.hpp"

namespace integrators::verlet {
void oscillator_step(ParticleOscillator &oscillator, double dt) {
  const double dt2 = dt * dt;
  // compute force with : -k * r - gamma * v
  // velocidad desfasada!! limitación del metodo ..
  double fx =
      -(oscillator.k * oscillator.r) - (oscillator.gamma * oscillator.vx);

  // calculate new position
  double r_new =
      2.0 * oscillator.r - oscillator.r_old + (dt2 / oscillator.m) * fx;

  // calculate new velocity
  // v(t) = [r(t+dt) - r(t-dt)] / (2 dt)
  oscillator.vx = (r_new - oscillator.r_old) / (2.0 * dt);

  // update position old and new
  oscillator.r_old = oscillator.r;
  oscillator.r = r_new;
}
} // namespace integrators::verlet

namespace integrators::beeman {

void oscillator_step(ParticleOscillator &oscillator, double dt) {
  const double dt2 = dt * dt;
  const double r = oscillator.r;
  const double v = oscillator.vx;
  const double a = oscillator.a_current; // a(t)
  const double a_old = oscillator.a_old; // a(t-dt)

  // r(t+dt)
  const double r_new =
      r + v * dt + (2.0 / 3.0) * a * dt2 - (1.0 / 6.0) * a_old * dt2;

  // predicción de v(t+dt), solo para evaluar a(t+dt)
  const double v_pred = v + 1.5 * a * dt - 0.5 * a_old * dt;

  // a(t+dt) con la velocidad predicha
  const double a_pred = acceleration(oscillator, r_new, v_pred);

  // corrector: v(t+dt)
  const double v_new = v + (1.0 / 3.0) * a_pred * dt + (5.0 / 6.0) * a * dt -
                       (1.0 / 6.0) * a_old * dt;

  // a(t+dt) consistente con la velocidad corregida, para el próximo paso
  const double a_new = acceleration(oscillator, r_new, v_new);

  // rotar estado
  oscillator.a_old = a;
  oscillator.a_current = a_new;
  oscillator.r = r_new;
  oscillator.vx = v_new;
}

} // namespace integrators::beeman
namespace integrators::velocity_verlet {

void oscillator_step(ParticleOscillator &oscillator, double dt) {

  const double r = oscillator.r;
  const double v = oscillator.vx;

  // calculo aceleración
  const double a = acceleration(oscillator, r, v);

  // r(t+dt) = r(t) + dt v(t) + dt^2/2 a(t)
  const double r_new = r + dt * v + 0.5 * dt * dt * a;

  // Paso intermedio 1: v(t+dt/2) = v(t) + a(t) dt/2
  const double v_half = v + 0.5 * dt * a;

  // Predicción de v(t+dt)
  const double v_pred = v + dt * a;

  // a(t+dt) con r(t+dt) y v predicha
  const double a_new = acceleration(oscillator, r_new, v_pred);

  // paso intermedio 2: v(t+dt) = v(t+dt/2) + a(t+dt) dt/2
  // (equivale a v + dt/2 (a(t) + a(t+dt)))
  oscillator.vx = v_half + 0.5 * dt * a_new;
  oscillator.r = r_new;
}

} // namespace integrators::velocity_verlet
namespace integrators::euler_predictor_corrector {
void oscillator_step(ParticleOscillator &oscillator, double dt) {
  const double r = oscillator.r;
  const double v = oscillator.vx;

  // a(t)
  const double a = acceleration(oscillator, r, v);

  // predecir
  const double v_p = v + a * dt;
  const double r_p = r + v * dt;

  // Evaluar a(t+dt) con las predicciones...
  const double a_new = acceleration(oscillator, r_p, v_p);

  // Corregir
  const double v_new = v + a_new * dt;
  const double r_new = r + v_new * dt;

  oscillator.vx = v_new;
  oscillator.r = r_new;
}

} // namespace integrators::euler_predictor_corrector
