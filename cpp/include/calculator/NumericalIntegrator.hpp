#pragma once

#include <functional>
#include <string>

namespace calculator {

struct IntegrationResult {
    double value = 0.0;
    double errorEstimate = 0.0;
    bool hasErrorEstimate = false;
};

class NumericalIntegrator {
public:
    using Function = std::function<double(double)>;
    using Progress = std::function<void(int)>;

    static IntegrationResult integrate(
        const std::string& method,
        const Function& function,
        double lower,
        double upper,
        double delta = 0.0,
        const Progress& progress = {}
    );

private:
    static double rectangle(const Function& function, double lower, double upper, int intervals);
    static double trapezoidal(const Function& function, double lower, double upper, int intervals);
    static double simpson(const Function& function, double lower, double upper, int intervals);
    static double simpson38(const Function& function, double lower, double upper, int intervals);
    static double romberg(const Function& function, double lower, double upper);
    static IntegrationResult gaussian(const Function& function, double lower, double upper, int points);
    static double adaptiveSimpson(const Function& function, double lower, double upper, double tolerance);
    static IntegrationResult monteCarlo(const Function& function, double lower, double upper, int samples);
    static IntegrationResult integrateInfinite(
        const std::string& method,
        const Function& function,
        double lower,
        double upper,
        double delta,
        const Progress& progress
    );
};

}  // namespace calculator

