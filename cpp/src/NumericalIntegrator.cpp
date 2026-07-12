#include "calculator/NumericalIntegrator.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <numbers>
#include <random>
#include <stdexcept>
#include <utility>
#include <vector>

namespace calculator {
namespace {

void requireFinite(double value) {
    if (!std::isfinite(value)) {
        throw std::runtime_error("Function produced a non-finite value.");
    }
}

int intervalCount(double lower, double upper, double delta, int fallback, int minimum) {
    if (delta <= 0.0) {
        return fallback;
    }
    return std::max(minimum, static_cast<int>(std::ceil(std::abs(upper - lower) / delta)));
}

double adaptiveRecursive(
    const NumericalIntegrator::Function& function,
    double lower,
    double upper,
    double fLower,
    double fMiddle,
    double fUpper,
    double whole,
    double tolerance,
    int depth
) {
    const double middle = (lower + upper) * 0.5;
    const double leftMiddle = (lower + middle) * 0.5;
    const double rightMiddle = (middle + upper) * 0.5;
    const double fLeftMiddle = function(leftMiddle);
    const double fRightMiddle = function(rightMiddle);
    requireFinite(fLeftMiddle);
    requireFinite(fRightMiddle);
    const double left = (middle - lower) * (fLower + 4.0 * fLeftMiddle + fMiddle) / 6.0;
    const double right = (upper - middle) * (fMiddle + 4.0 * fRightMiddle + fUpper) / 6.0;
    const double correction = left + right - whole;
    if (depth <= 0 || std::abs(correction) <= 15.0 * tolerance) {
        return left + right + correction / 15.0;
    }
    return adaptiveRecursive(
               function, lower, middle, fLower, fLeftMiddle, fMiddle,
               left, tolerance * 0.5, depth - 1
           ) +
           adaptiveRecursive(
               function, middle, upper, fMiddle, fRightMiddle, fUpper,
               right, tolerance * 0.5, depth - 1
           );
}

std::pair<std::vector<double>, std::vector<double>> gaussLegendreRule(int points) {
    std::vector<double> nodes(points);
    std::vector<double> weights(points);
    const int half = (points + 1) / 2;
    for (int index = 0; index < half; ++index) {
        double root = std::cos(std::numbers::pi * (index + 0.75) / (points + 0.5));
        double derivative = 0.0;
        for (int iteration = 0; iteration < 32; ++iteration) {
            double previous = 1.0;
            double current = root;
            for (int order = 2; order <= points; ++order) {
                const double next = ((2.0 * order - 1.0) * root * current - (order - 1.0) * previous) / order;
                previous = current;
                current = next;
            }
            derivative = points * (root * current - previous) / (root * root - 1.0);
            const double nextRoot = root - current / derivative;
            if (std::abs(nextRoot - root) < 1e-15) {
                root = nextRoot;
                break;
            }
            root = nextRoot;
        }
        const double weight = 2.0 / ((1.0 - root * root) * derivative * derivative);
        nodes[index] = -root;
        nodes[points - 1 - index] = root;
        weights[index] = weight;
        weights[points - 1 - index] = weight;
    }
    return {std::move(nodes), std::move(weights)};
}

}  // namespace

IntegrationResult NumericalIntegrator::integrate(
    const std::string& method,
    const Function& function,
    double lower,
    double upper,
    double delta,
    const Progress& progress
) {
    if (!std::isfinite(lower) || !std::isfinite(upper)) {
        return integrateInfinite(method, function, lower, upper, delta, progress);
    }
    if (lower == upper) {
        return {};
    }
    IntegrationResult result;
    if (method == "Rectangle") {
        result.value = rectangle(function, lower, upper, intervalCount(lower, upper, delta, 1000, 10));
    } else if (method == "Trapezoidal") {
        result.value = trapezoidal(function, lower, upper, intervalCount(lower, upper, delta, 2000, 50));
    } else if (method == "Simpson") {
        result.value = simpson(function, lower, upper, intervalCount(lower, upper, delta, 2000, 100));
    } else if (method == "Simpson 3/8") {
        result.value = simpson38(function, lower, upper, intervalCount(lower, upper, delta, 300, 30));
    } else if (method == "Romberg") {
        result.value = romberg(function, lower, upper);
    } else if (method == "Gaussian Quadrature") {
        result = gaussian(function, lower, upper, 64);
    } else if (method == "Adaptive Simpson") {
        result.value = adaptiveSimpson(function, lower, upper, 1e-9);
    } else if (method == "Monte Carlo") {
        result = monteCarlo(function, lower, upper, intervalCount(lower, upper, delta, 8000, 4000));
    } else {
        throw std::invalid_argument("Unknown numerical method: " + method);
    }
    if (progress) {
        progress(100);
    }
    return result;
}

double NumericalIntegrator::rectangle(const Function& function, double lower, double upper, int intervals) {
    const double width = (upper - lower) / intervals;
    double sum = 0.0;
    for (int index = 0; index < intervals; ++index) {
        const double value = function(lower + (index + 0.5) * width);
        requireFinite(value);
        sum += value;
    }
    return sum * width;
}

double NumericalIntegrator::trapezoidal(const Function& function, double lower, double upper, int intervals) {
    const double width = (upper - lower) / intervals;
    double sum = 0.5 * (function(lower) + function(upper));
    requireFinite(sum);
    for (int index = 1; index < intervals; ++index) {
        const double value = function(lower + index * width);
        requireFinite(value);
        sum += value;
    }
    return sum * width;
}

double NumericalIntegrator::simpson(const Function& function, double lower, double upper, int intervals) {
    if (intervals % 2 != 0) {
        ++intervals;
    }
    const double width = (upper - lower) / intervals;
    double sum = function(lower) + function(upper);
    requireFinite(sum);
    for (int index = 1; index < intervals; ++index) {
        const double value = function(lower + index * width);
        requireFinite(value);
        sum += (index % 2 == 0 ? 2.0 : 4.0) * value;
    }
    return sum * width / 3.0;
}

double NumericalIntegrator::simpson38(const Function& function, double lower, double upper, int intervals) {
    intervals += (3 - intervals % 3) % 3;
    const double width = (upper - lower) / intervals;
    double sum = function(lower) + function(upper);
    requireFinite(sum);
    for (int index = 1; index < intervals; ++index) {
        const double value = function(lower + index * width);
        requireFinite(value);
        sum += (index % 3 == 0 ? 2.0 : 3.0) * value;
    }
    return 3.0 * width * sum / 8.0;
}

double NumericalIntegrator::romberg(const Function& function, double lower, double upper) {
    constexpr int levels = 9;
    double table[levels][levels] = {};
    table[0][0] = 0.5 * (upper - lower) * (function(lower) + function(upper));
    for (int level = 1; level < levels; ++level) {
        const int newPoints = 1 << (level - 1);
        const double step = (upper - lower) / (1 << level);
        double sum = 0.0;
        for (int index = 1; index <= newPoints; ++index) {
            sum += function(lower + (2 * index - 1) * step);
        }
        table[level][0] = 0.5 * table[level - 1][0] + step * sum;
        for (int order = 1; order <= level; ++order) {
            const double factor = std::pow(4.0, order);
            table[level][order] = table[level][order - 1] +
                (table[level][order - 1] - table[level - 1][order - 1]) / (factor - 1.0);
        }
        if (std::abs(table[level][level] - table[level - 1][level - 1]) < 1e-10) {
            return table[level][level];
        }
    }
    return table[levels - 1][levels - 1];
}

IntegrationResult NumericalIntegrator::gaussian(const Function& function, double lower, double upper, int points) {
    static const auto rule64 = gaussLegendreRule(64);
    static const auto rule32 = gaussLegendreRule(32);
    const auto evaluateRule = [&](const auto& rule) {
        const double center = (lower + upper) * 0.5;
        const double scale = (upper - lower) * 0.5;
        double sum = 0.0;
        for (std::size_t index = 0; index < rule.first.size(); ++index) {
            const double value = function(center + scale * rule.first[index]);
            requireFinite(value);
            sum += rule.second[index] * value;
        }
        return scale * sum;
    };
    const double fine = evaluateRule(points >= 64 ? rule64 : rule32);
    const double coarse = evaluateRule(rule32);
    return {fine, std::abs(fine - coarse), true};
}

double NumericalIntegrator::adaptiveSimpson(
    const Function& function,
    double lower,
    double upper,
    double tolerance
) {
    const double middle = (lower + upper) * 0.5;
    const double fLower = function(lower);
    const double fMiddle = function(middle);
    const double fUpper = function(upper);
    requireFinite(fLower);
    requireFinite(fMiddle);
    requireFinite(fUpper);
    const double whole = (upper - lower) * (fLower + 4.0 * fMiddle + fUpper) / 6.0;
    return adaptiveRecursive(function, lower, upper, fLower, fMiddle, fUpper, whole, tolerance, 20);
}

IntegrationResult NumericalIntegrator::monteCarlo(
    const Function& function,
    double lower,
    double upper,
    int samples
) {
    std::mt19937_64 generator(std::random_device{}());
    std::uniform_real_distribution<double> distribution(lower, upper);
    double mean = 0.0;
    double m2 = 0.0;
    for (int index = 1; index <= samples; ++index) {
        const double value = function(distribution(generator));
        requireFinite(value);
        const double delta = value - mean;
        mean += delta / index;
        m2 += delta * (value - mean);
    }
    const double width = upper - lower;
    const double variance = samples > 1 ? m2 / (samples - 1) : 0.0;
    return {width * mean, std::abs(width) * std::sqrt(variance / samples), true};
}

IntegrationResult NumericalIntegrator::integrateInfinite(
    const std::string& method,
    const Function& function,
    double lower,
    double upper,
    double delta,
    const Progress& progress
) {
    if (method != "Adaptive Simpson") {
        throw std::invalid_argument("Only Adaptive Simpson supports infinite limits.");
    }
    constexpr double epsilon = 1e-7;
    Function transformed;
    if (!std::isfinite(lower) && !std::isfinite(upper)) {
        transformed = [function](double t) {
            const double angle = std::numbers::pi * (t - 0.5);
            const double cosine = std::cos(angle);
            return function(std::tan(angle)) * std::numbers::pi / (cosine * cosine);
        };
    } else if (std::isfinite(lower)) {
        transformed = [function, lower](double t) {
            const double denominator = 1.0 - t;
            return function(lower + t / denominator) / (denominator * denominator);
        };
    } else {
        transformed = [function, upper](double t) {
            const double denominator = 1.0 - t;
            return function(upper - t / denominator) / (denominator * denominator);
        };
    }
    IntegrationResult result;
    result.value = adaptiveSimpson(transformed, epsilon, 1.0 - epsilon, 1e-8);
    if (progress) {
        progress(100);
    }
    return result;
}

}  // namespace calculator

