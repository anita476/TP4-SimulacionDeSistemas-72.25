#pragma once
#include "oscillator.hpp"

namespace integrators {
inline double acceleration(const ParticleOscillator &o, double r, double v) {
  return (-(o.k * r) - (o.gamma * v)) / o.m;
}
using Step = void (*)(ParticleOscillator &, double dt);

namespace verlet {
void oscillator_step(ParticleOscillator &, double dt);

}
namespace beeman {
void oscillator_step(ParticleOscillator &, double dt);

}
namespace velocity_verlet {
void oscillator_step(ParticleOscillator &, double dt);

}
namespace euler_predictor_corrector {
void oscillator_step(ParticleOscillator &, double dt);

}
} // namespace integrators