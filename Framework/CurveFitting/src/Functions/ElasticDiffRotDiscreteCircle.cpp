// Mantid Coding standards <http://www.mantidproject.org/Coding_Standards>
// Main Module Header
#include "MantidCurveFitting/Functions/ElasticDiffRotDiscreteCircle.h"
// Mantid Headers from the same project
#include "MantidCurveFitting/Constraints/BoundaryConstraint.h"
// Mantid headers from other projects
#include "MantidAPI/FunctionFactory.h"
#include "MantidAPI/IFunction.h"
// 3rd party library headers (N/A)
// standard library headers
#include <cmath>
#include <limits>

using BConstraint = Mantid::CurveFitting::Constraints::BoundaryConstraint;

namespace {
Mantid::Kernel::Logger g_log("ElasticDiffRotDiscreteCircle");
}

namespace Mantid {
namespace CurveFitting {
namespace Functions {

DECLARE_FUNCTION(ElasticDiffRotDiscreteCircle)

/**
 * @brief Constructor where fitting parameters are declared
 */
ElasticDiffRotDiscreteCircle::ElasticDiffRotDiscreteCircle() {
  // declareParameter("Height", 1.0); //parameter "Height" already declared in
  // constructor of base class DeltaFunction
  this->declareParameter("Radius", 1.0, "Circle radius [Angstroms] ");
  this->declareAttribute("Q", API::IFunction::Attribute(0.5));
  this->declareAttribute("N", API::IFunction::Attribute(3));
}

/**
 * @brief Set constraints on fitting parameters
 */
void ElasticDiffRotDiscreteCircle::init() {
  // Ensure positive values for Height and Radius
  auto HeightConstraint = new BConstraint(
      this, "Height", std::numeric_limits<double>::epsilon(), true);
  this->addConstraint(HeightConstraint);

  auto RadiusConstraint = new BConstraint(
      this, "Radius", std::numeric_limits<double>::epsilon(), true);
  this->addConstraint(RadiusConstraint);
}

/**
 * @brief Calculate intensity of the elastic signal
 */
double ElasticDiffRotDiscreteCircle::HeightPrefactor() const {
  auto R = this->getParameter("Radius");
  auto Q = this->getAttribute("Q").asDouble();
  auto N = this->getAttribute("N").asInt();
  double aN = 0;
  for (int k = 1; k < N; k++) {
    double x = 2 * Q * R * sin(M_PI * k / N);
    aN += sin(x) / x; // spherical Besell function of order zero j0==sin(x)/x
  }
  aN += 1; // limit for j0 when k==N, or x==0
  return aN / N;
}

} // namespace Functions
} // namespace CurveFitting
} // namespace Mantid