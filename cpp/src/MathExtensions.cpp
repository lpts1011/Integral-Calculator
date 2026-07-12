#include "calculator/MathExtensions.hpp"

#include "calculator/ExpressionEngine.hpp"
#include "calculator/NumericalIntegrator.hpp"
#include "calculator/SymbolicEngine.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <iomanip>
#include <numbers>
#include <numeric>
#include <regex>
#include <sstream>
#include <stdexcept>

namespace calculator {
namespace {

std::string trim(std::string value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return {};
    }
    return value.substr(first, value.find_last_not_of(" \t\r\n") - first + 1);
}

std::string numberText(double value, int precision = 10) {
    if (std::abs(value) < 1e-13) {
        return "0";
    }
    const double piRatio = value / std::numbers::pi;
    for (int denominator = 1; denominator <= 24; ++denominator) {
        const double numerator = std::round(piRatio * denominator);
        if (std::abs(piRatio - numerator / denominator) < 1e-10) {
            if (denominator == 1) {
                if (numerator == 1) return "pi";
                if (numerator == -1) return "-pi";
                return std::to_string(static_cast<int>(numerator)) + "*pi";
            }
            return std::to_string(static_cast<int>(numerator)) + "*pi/" +
                   std::to_string(denominator);
        }
    }
    for (int denominator = 1; denominator <= 1000; ++denominator) {
        const double numerator = std::round(value * denominator);
        if (std::abs(value - numerator / denominator) < 1e-11) {
            if (denominator == 1) return std::to_string(static_cast<long long>(numerator));
            return std::to_string(static_cast<long long>(numerator)) + "/" +
                   std::to_string(denominator);
        }
    }
    std::ostringstream stream;
    stream << std::setprecision(precision) << value;
    return stream.str();
}

double integrate1d(const NumericalIntegrator::Function& function, double lower, double upper) {
    return NumericalIntegrator::integrate("Adaptive Simpson", function, lower, upper).value;
}

double derivative(const NumericalIntegrator::Function& function, double x, double h = 1e-5) {
    return (-function(x + 2 * h) + 8 * function(x + h) - 8 * function(x - h) +
            function(x - 2 * h)) / (12 * h);
}

double secondDerivative(const NumericalIntegrator::Function& function, double x, double h = 1e-4) {
    return (function(x + h) - 2 * function(x) + function(x - h)) / (h * h);
}

std::vector<double> scanZeros(const NumericalIntegrator::Function& function, double lower, double upper) {
    std::vector<double> roots;
    constexpr int samples = 1600;
    double previousX = lower;
    double previous = 0.0;
    bool previousValid = false;
    for (int index = 0; index <= samples; ++index) {
        const double x = lower + (upper - lower) * index / samples;
        try {
            const double value = function(x);
            if (std::abs(value) < 1e-7) {
                if (roots.empty() || std::abs(x - roots.back()) > (upper - lower) / samples * 2) {
                    roots.push_back(x);
                }
            } else if (previousValid && std::signbit(value) != std::signbit(previous)) {
                double left = previousX;
                double right = x;
                for (int step = 0; step < 60; ++step) {
                    const double middle = (left + right) / 2;
                    if (std::signbit(function(middle)) == std::signbit(function(left))) left = middle;
                    else right = middle;
                }
                const double root = (left + right) / 2;
                if (roots.empty() || std::abs(root - roots.back()) > 1e-5) roots.push_back(root);
            }
            previous = value;
            previousX = x;
            previousValid = true;
        } catch (...) {
            previousValid = false;
        }
    }
    for (double& root : roots) {
        if (std::abs(root) < 1e-8) root = 0.0;
        root = std::round(root * 1e9) / 1e9;
    }
    return roots;
}

long long binomial(int n, int k) {
    if (k < 0 || k > n) return 0;
    long long result = 1;
    for (int index = 1; index <= k; ++index) result = result * (n - index + 1) / index;
    return result;
}

double nthDerivative(const NumericalIntegrator::Function& function, double x, int order) {
    if (order == 0) return function(x);
    const double h = order <= 3 ? 2e-3 : 1e-2;
    double sum = 0.0;
    for (int k = 0; k <= order; ++k) {
        sum += (k % 2 ? -1.0 : 1.0) * binomial(order, k) *
               function(x + (order / 2.0 - k) * h);
    }
    return sum / std::pow(h, order);
}

double factorial(int value) {
    double result = 1.0;
    for (int index = 2; index <= value; ++index) result *= index;
    return result;
}

}  // namespace

ScalarToolResult MathExtensions::polarArea(const std::string& radius, double lower, double upper) {
    VariableExpressionEngine engine(radius, {"theta", "t"});
    const double value = 0.5 * integrate1d([&](double theta) {
        engine.setVariable("theta", theta);
        engine.setVariable("t", theta);
        const double r = engine.evaluate();
        return r * r;
    }, lower, upper);
    return {numberText(value), value, "Integrand: 1/2 * r(theta)^2"};
}

std::string MathExtensions::taylorPolynomial(
    const std::string& expression, double point, int order
) {
    if (order < 0 || order > 12) throw std::invalid_argument("Taylor order must be between 0 and 12.");
    ExpressionEngine engine(expression);
    const auto function = [&](double x) { return engine.evaluate(x); };
    std::ostringstream result;
    bool wrote = false;
    for (int n = 0; n <= order; ++n) {
        double coefficient = nthDerivative(function, point, n) / factorial(n);
        if (std::abs(coefficient) < 1e-7) continue;
        if (wrote) result << (coefficient >= 0 ? " + " : " - ");
        else if (coefficient < 0) result << "-";
        coefficient = std::abs(coefficient);
        if (n == 0 || std::abs(coefficient - 1.0) > 1e-7) result << numberText(coefficient, 7);
        if (n > 0) {
            if (n == 0 || std::abs(coefficient - 1.0) > 1e-7) result << "*";
            result << (std::abs(point) < 1e-14 ? "x" : "(x-" + numberText(point) + ")");
            if (n > 1) result << "^" << n;
        }
        wrote = true;
    }
    return wrote ? result.str() : "0";
}

std::vector<NumericTableRow> MathExtensions::convergenceTable(
    const std::string& expression, double lower, double upper,
    const std::string& method, const std::vector<int>& intervals
) {
    ExpressionEngine engine(expression);
    const auto function = [&](double x) { return engine.evaluate(x); };
    const double reference = integrate1d(function, lower, upper);
    std::vector<NumericTableRow> rows;
    for (int count : intervals) {
        if (count <= 0) continue;
        const double delta = std::abs(upper - lower) / count;
        const auto value = NumericalIntegrator::integrate(method, function, lower, upper, delta);
        rows.push_back({std::to_string(count), {delta, value.value, std::abs(value.value - reference)}});
    }
    if (rows.empty()) throw std::invalid_argument("Enter at least one positive interval count.");
    return rows;
}

FunctionAnalysis MathExtensions::analyzeFunction(
    const std::string& expression, double lower, double upper
) {
    ExpressionEngine engine(expression);
    const auto function = [&](double x) { return engine.evaluate(x); };
    FunctionAnalysis result;
    result.roots = scanZeros(function, lower, upper);
    result.criticalPoints = scanZeros([&](double x) { return derivative(function, x); }, lower, upper);
    result.inflectionPoints = scanZeros([&](double x) { return secondDerivative(function, x); }, lower, upper);
    constexpr int samples = 1200;
    for (int index = 1; index < samples; ++index) {
        const double x = lower + (upper - lower) * index / samples;
        try {
            const double value = function(x);
            if (std::abs(value) > 1e8) result.singularities.push_back(x);
        } catch (...) {
            result.singularities.push_back(x);
        }
    }
    if (!result.singularities.empty()) {
        std::vector<double> merged;
        for (double value : result.singularities) {
            if (merged.empty() || std::abs(value - merged.back()) > (upper - lower) / samples * 3) {
                merged.push_back(value);
            }
        }
        result.singularities = std::move(merged);
    }
    return result;
}

ScalarToolResult MathExtensions::averageValue(
    const std::string& expression, double lower, double upper
) {
    if (lower == upper) throw std::invalid_argument("Average value requires different limits.");
    ExpressionEngine engine(expression);
    const double integral = integrate1d([&](double x) { return engine.evaluate(x); }, lower, upper);
    const double average = integral / (upper - lower);
    return {numberText(average), average, "Integral: " + numberText(integral)};
}

std::vector<double> MathExtensions::areaBreakdown(
    const std::string& expression, double lower, double upper
) {
    ExpressionEngine engine(expression);
    const auto f = [&](double x) { return engine.evaluate(x); };
    const double signedArea = integrate1d(f, lower, upper);
    const double absoluteArea = integrate1d([&](double x) { return std::abs(f(x)); }, lower, upper);
    const double positive = integrate1d([&](double x) { return std::max(0.0, f(x)); }, lower, upper);
    const double negative = integrate1d([&](double x) { return std::max(0.0, -f(x)); }, lower, upper);
    return {signedArea, absoluteArea, positive, negative};
}

ScalarToolResult MathExtensions::arcLength(
    const std::string& expression, double lower, double upper
) {
    ExpressionEngine engine(expression);
    const auto f = [&](double x) { return engine.evaluate(x); };
    const double value = integrate1d([&](double x) {
        const double slope = derivative(f, x);
        return std::sqrt(1 + slope * slope);
    }, lower, upper);
    return {numberText(value), value, "Integral of sqrt(1 + (f'(x))^2)"};
}

ScalarToolResult MathExtensions::revolutionVolume(
    const std::string& expression, double lower, double upper, char axis
) {
    ExpressionEngine engine(expression);
    const double value = integrate1d([&](double x) {
        const double y = engine.evaluate(x);
        return axis == 'y' ? 2 * std::numbers::pi * x * y : std::numbers::pi * y * y;
    }, lower, upper);
    return {numberText(value), value, axis == 'y' ? "Shell method" : "Disk method"};
}

std::string MathExtensions::fourierSeries(
    const std::string& expression, double period, int terms
) {
    if (period <= 0 || terms <= 0) throw std::invalid_argument("Period and terms must be positive.");
    ExpressionEngine engine(expression);
    const double half = period / 2;
    const double a0 = 2 / period * integrate1d([&](double x) { return engine.evaluate(x); }, -half, half);
    std::ostringstream result;
    result << numberText(a0 / 2, 7);
    for (int n = 1; n <= terms; ++n) {
        const double frequency = 2 * std::numbers::pi * n / period;
        const double an = 2 / period * integrate1d([&](double x) {
            return engine.evaluate(x) * std::cos(frequency * x);
        }, -half, half);
        const double bn = 2 / period * integrate1d([&](double x) {
            return engine.evaluate(x) * std::sin(frequency * x);
        }, -half, half);
        if (std::abs(an) > 1e-8) result << (an >= 0 ? " + " : " - ") << numberText(std::abs(an), 7)
                                      << "*cos(" << n << "*2*pi*x/" << numberText(period) << ")";
        if (std::abs(bn) > 1e-8) result << (bn >= 0 ? " + " : " - ") << numberText(std::abs(bn), 7)
                                      << "*sin(" << n << "*2*pi*x/" << numberText(period) << ")";
    }
    return result.str();
}

std::string MathExtensions::laplaceTransform(const std::string& expression) {
    const std::string value = ExpressionEngine::normalize(trim(expression));
    std::smatch match;
    if (value == "1") return "1/s";
    if (value == "x") return "1/s^2";
    if (std::regex_match(value, match, std::regex(R"(exp\(-([0-9.]+)\*?x\))"))) {
        return "1/(s + " + match[1].str() + ")";
    }
    if (value == "exp(-x)") return "1/(s + 1)";
    if (std::regex_match(value, match, std::regex(R"(sin\(([0-9.]*)\*?x\))"))) {
        const std::string a = match[1].str().empty() ? "1" : match[1].str();
        return a + "/(s^2 + " + a + "^2)";
    }
    if (std::regex_match(value, match, std::regex(R"(cos\(([0-9.]*)\*?x\))"))) {
        const std::string a = match[1].str().empty() ? "1" : match[1].str();
        return "s/(s^2 + " + a + "^2)";
    }
    return "L{" + value + "}(s) = integral[0, inf] " + value + "*exp(-s*x) dx";
}

std::string MathExtensions::solveOde(const std::string& equation) {
    std::string value = trim(equation);
    value.erase(std::remove_if(value.begin(), value.end(), [](unsigned char c) {
        return std::isspace(c) != 0;
    }), value.end());
    const auto equal = value.find('=');
    if (equal == std::string::npos || value.substr(0, equal) != "y'") {
        throw std::invalid_argument("Enter a first-order equation such as y' = x*y.");
    }
    std::string rhs = value.substr(equal + 1);
    if (rhs == "x*y" || rhs == "y*x") return "y = C*exp(x^2/2)";
    if (rhs == "y") return "y = C*exp(x)";
    if (rhs == "-y") return "y = C*exp(-x)";
    if (rhs.ends_with("*y")) {
        const std::string coefficient = rhs.substr(0, rhs.size() - 2);
        const auto integral = SymbolicEngine::antiderivative(coefficient);
        if (integral.closedForm) return "y = C*exp(" + integral.expression + ")";
    }
    const auto integral = SymbolicEngine::antiderivative(rhs);
    if (integral.closedForm) return "y = " + integral.expression + " + C";
    throw std::invalid_argument("No native closed-form solution is available for this equation.");
}

std::vector<NumericTableRow> MathExtensions::errorProfile(
    const std::string& expression, double lower, double upper
) {
    ExpressionEngine engine(expression);
    const auto f = [&](double x) { return engine.evaluate(x); };
    const double reference = integrate1d(f, lower, upper);
    std::vector<NumericTableRow> rows;
    for (const std::string method : {
             "Rectangle", "Trapezoidal", "Simpson", "Gaussian Quadrature", "Adaptive Simpson"
         }) {
        const auto result = NumericalIntegrator::integrate(method, f, lower, upper);
        rows.push_back({method, {result.value, std::abs(result.value - reference), result.errorEstimate}});
    }
    return rows;
}

ScalarToolResult MathExtensions::doubleIntegral(
    const std::string& expression, double xLower, double xUpper,
    double yLower, double yUpper
) {
    VariableExpressionEngine engine(expression, {"x", "y"});
    const double value = integrate1d([&](double x) {
        engine.setVariable("x", x);
        return integrate1d([&](double y) {
            engine.setVariable("y", y);
            return engine.evaluate();
        }, yLower, yUpper);
    }, xLower, xUpper);
    return {numberText(value), value, "Rectangular double integral"};
}

ScalarToolResult MathExtensions::variableDoubleIntegral(
    const std::string& expression, double xLower, double xUpper,
    const std::string& yLower, const std::string& yUpper
) {
    VariableExpressionEngine engine(expression, {"x", "y"});
    VariableExpressionEngine lowerEngine(yLower, {"x"});
    VariableExpressionEngine upperEngine(yUpper, {"x"});
    const double value = integrate1d([&](double x) {
        engine.setVariable("x", x);
        lowerEngine.setVariable("x", x);
        upperEngine.setVariable("x", x);
        return integrate1d([&](double y) {
            engine.setVariable("y", y);
            return engine.evaluate();
        }, lowerEngine.evaluate(), upperEngine.evaluate());
    }, xLower, xUpper);
    return {numberText(value), value, "Variable-bound double integral"};
}

ScalarToolResult MathExtensions::polarDoubleIntegral(
    const std::string& expression, double rLower, double rUpper,
    double thetaLower, double thetaUpper
) {
    VariableExpressionEngine engine(expression, {"r", "theta", "t"});
    const double value = integrate1d([&](double theta) {
        engine.setVariable("theta", theta);
        engine.setVariable("t", theta);
        return integrate1d([&](double r) {
            engine.setVariable("r", r);
            return engine.evaluate() * r;
        }, rLower, rUpper);
    }, thetaLower, thetaUpper);
    return {numberText(value), value, "Polar double integral with Jacobian r"};
}

ScalarToolResult MathExtensions::tripleIntegral(
    const std::string& expression, double xLower, double xUpper,
    double yLower, double yUpper, double zLower, double zUpper
) {
    VariableExpressionEngine engine(expression, {"x", "y", "z"});
    const double value = integrate1d([&](double x) {
        engine.setVariable("x", x);
        return integrate1d([&](double y) {
            engine.setVariable("y", y);
            return integrate1d([&](double z) {
                engine.setVariable("z", z);
                return engine.evaluate();
            }, zLower, zUpper);
        }, yLower, yUpper);
    }, xLower, xUpper);
    return {numberText(value), value, "Rectangular triple integral"};
}

std::vector<NumericTableRow> MathExtensions::parameterSensitivity(
    const std::string& expression, const std::string& parameter,
    const std::vector<double>& values, double lower, double upper
) {
    if (parameter.empty()) throw std::invalid_argument("Parameter name is required.");
    std::vector<NumericTableRow> rows;
    for (double value : values) {
        ExpressionEngine engine(expression, {{parameter, value}});
        const double integral = integrate1d([&](double x) { return engine.evaluate(x); }, lower, upper);
        rows.push_back({numberText(value), {integral}});
    }
    return rows;
}

bool MathExtensions::verifyAntiderivative(
    const std::string& expression, const std::string& antiderivative, double* maximumError
) {
    ExpressionEngine original(expression);
    ExpressionEngine candidate(antiderivative);
    double maxError = 0.0;
    for (int index = 0; index <= 80; ++index) {
        const double x = -3.0 + 6.0 * index / 80.0;
        try {
            maxError = std::max(maxError, std::abs(derivative(
                [&](double point) { return candidate.evaluate(point); }, x
            ) - original.evaluate(x)));
        } catch (...) {
        }
    }
    if (maximumError) *maximumError = maxError;
    return maxError < 1e-5;
}

std::string MathExtensions::buildPiecewise(
    const std::vector<std::pair<std::string, std::string>>& pieces
) {
    std::vector<std::pair<std::string, std::string>> cleaned;
    for (const auto& [expression, condition] : pieces) {
        if (!trim(expression).empty()) cleaned.emplace_back(trim(expression), trim(condition).empty() ? "True" : trim(condition));
    }
    if (cleaned.empty()) throw std::invalid_argument("Add at least one piece.");
    if (std::none_of(cleaned.begin(), cleaned.end(), [](const auto& item) {
            std::string condition = item.second;
            std::transform(condition.begin(), condition.end(), condition.begin(), ::tolower);
            return condition == "true";
        })) {
        cleaned.emplace_back(cleaned.back().first, "True");
    }
    std::string result = "Piecewise(";
    for (std::size_t index = 0; index < cleaned.size(); ++index) {
        if (index) result += ", ";
        result += "(" + cleaned[index].first + ", " + cleaned[index].second + ")";
    }
    return result + ")";
}

std::string MathExtensions::parameterAssignment(const std::string& name, double value) {
    if (trim(name).empty()) throw std::invalid_argument("Parameter name is required.");
    return trim(name) + "=" + numberText(value, 6);
}

std::string MathExtensions::substitutionHelp(
    const std::string& expression, const std::string& substitution
) {
    return "Let " + substitution + ". Rewrite " + expression + " using u and du, then integrate in u.";
}

std::string MathExtensions::integrationByPartsHelp(
    const std::string& u, const std::string& dv
) {
    const auto v = SymbolicEngine::antiderivative(dv);
    return "Use integral u dv = u*v - integral v du. u=" + u +
           ", dv=" + dv + ", v=" + (v.closedForm ? v.expression : "not available") + ".";
}

}  // namespace calculator
