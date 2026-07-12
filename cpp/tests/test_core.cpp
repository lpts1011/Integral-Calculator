#include "calculator/ExpressionEngine.hpp"
#include "calculator/MathExtensions.hpp"
#include "calculator/NumericalIntegrator.hpp"
#include "calculator/SymbolicEngine.hpp"

#include <cmath>
#include <iostream>
#include <limits>
#include <numbers>
#include <stdexcept>
#include <string>

namespace {

void requireNear(double actual, double expected, double tolerance, const std::string& name) {
    if (std::abs(actual - expected) > tolerance) {
        throw std::runtime_error(
            name + " failed: expected " + std::to_string(expected) +
            ", got " + std::to_string(actual)
        );
    }
}

}  // namespace

int main() {
    using calculator::ExpressionEngine;
    using calculator::MathExtensions;
    using calculator::NumericalIntegrator;
    using calculator::SymbolicEngine;
    using calculator::VariableExpressionEngine;

    ExpressionEngine expression("a*x^2 + sin(x)", {{"a", 2.0}});
    requireNear(expression.evaluate(1.0), 2.0 + std::sin(1.0), 1e-12, "expression parser");
    const auto substituted = ExpressionEngine::substituteParameters(
        "a*x+b", {{"a", 2.0}, {"b", 3.0}}
    );
    if (substituted != "2*x+3") {
        throw std::runtime_error("parameter substitution failed: " + substituted);
    }
    VariableExpressionEngine multivariable("x + 2*y + z", {"x", "y", "z"});
    multivariable.setVariable("x", 1.0);
    multivariable.setVariable("y", 2.0);
    multivariable.setVariable("z", 3.0);
    requireNear(multivariable.evaluate(), 8.0, 1e-12, "multivariable parser");

    const auto function = [](double x) { return x * x; };
    for (const std::string method : {
             "Rectangle", "Trapezoidal", "Simpson", "Simpson 3/8",
             "Romberg", "Gaussian Quadrature", "Adaptive Simpson"
         }) {
        const auto result = NumericalIntegrator::integrate(method, function, 0.0, 1.0);
        requireNear(result.value, 1.0 / 3.0, 2e-6, method);
    }

    const auto sine = NumericalIntegrator::integrate(
        "Adaptive Simpson",
        [](double x) { return std::sin(x); },
        0.0,
        std::numbers::pi
    );
    requireNear(sine.value, 2.0, 1e-9, "adaptive sine");

    const auto improper = NumericalIntegrator::integrate(
        "Adaptive Simpson",
        [](double x) { return std::exp(-x); },
        0.0,
        std::numeric_limits<double>::infinity()
    );
    requireNear(improper.value, 1.0, 2e-6, "improper exponential");

    const auto symbolic = SymbolicEngine::antiderivative("x^2+sin(x)");
    if (!symbolic.closedForm) {
        throw std::runtime_error("symbolic antiderivative failed");
    }
    const auto exact = SymbolicEngine::definiteIntegral("x^2", 0.0, 1.0);
    if (!exact) {
        throw std::runtime_error("symbolic definite integral failed");
    }
    requireNear(*exact, 1.0 / 3.0, 1e-12, "symbolic definite integral");

    requireNear(
        MathExtensions::polarArea("2*cos(theta)", -std::numbers::pi / 2, std::numbers::pi / 2).numeric,
        std::numbers::pi,
        1e-8,
        "polar area"
    );
    requireNear(MathExtensions::averageValue("x", 0, 2).numeric, 1.0, 1e-9, "average value");
    requireNear(MathExtensions::arcLength("x", 0, 1).numeric, std::sqrt(2.0), 1e-7, "arc length");
    requireNear(
        MathExtensions::revolutionVolume("x", 0, 1, 'x').numeric,
        std::numbers::pi / 3,
        1e-8,
        "revolution volume"
    );
    requireNear(
        MathExtensions::doubleIntegral("x+y", 0, 1, 0, 1).numeric,
        1.0,
        1e-8,
        "double integral"
    );
    requireNear(
        MathExtensions::variableDoubleIntegral("1", 0, 1, "0", "x").numeric,
        0.5,
        1e-8,
        "variable double integral"
    );
    requireNear(
        MathExtensions::polarDoubleIntegral("1", 0, 1, 0, 2 * std::numbers::pi).numeric,
        std::numbers::pi,
        1e-8,
        "polar double integral"
    );
    requireNear(
        MathExtensions::tripleIntegral("1", 0, 1, 0, 1, 0, 1).numeric,
        1.0,
        1e-8,
        "triple integral"
    );
    const auto sensitivity = MathExtensions::parameterSensitivity("a*x", "a", {1, 2}, 0, 1);
    requireNear(sensitivity.at(0).values.at(0), 0.5, 1e-8, "parameter sensitivity 1");
    requireNear(sensitivity.at(1).values.at(0), 1.0, 1e-8, "parameter sensitivity 2");
    if (MathExtensions::laplaceTransform("exp(-x)") != "1/(s + 1)") {
        throw std::runtime_error("Laplace transform failed");
    }
    if (MathExtensions::solveOde("y' = x*y").find("exp(x^2/2)") == std::string::npos) {
        throw std::runtime_error("ODE solution failed");
    }
    double verificationError = 0.0;
    if (!MathExtensions::verifyAntiderivative("sin(x)", "-cos(x)", &verificationError)) {
        throw std::runtime_error("antiderivative verification failed");
    }

    std::cout << "All C++ core tests passed.\n";
    return 0;
}
