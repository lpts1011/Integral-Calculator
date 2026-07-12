#pragma once

#include <string>
#include <utility>
#include <vector>

namespace calculator {

struct ScalarToolResult {
    std::string exact;
    double numeric = 0.0;
    std::string details;
};

struct NumericTableRow {
    std::string label;
    std::vector<double> values;
};

struct FunctionAnalysis {
    std::vector<double> roots;
    std::vector<double> criticalPoints;
    std::vector<double> inflectionPoints;
    std::vector<double> singularities;
};

class MathExtensions {
public:
    static ScalarToolResult polarArea(
        const std::string& radius,
        double lower,
        double upper
    );
    static std::string taylorPolynomial(
        const std::string& expression,
        double point,
        int order
    );
    static std::vector<NumericTableRow> convergenceTable(
        const std::string& expression,
        double lower,
        double upper,
        const std::string& method,
        const std::vector<int>& intervals
    );
    static FunctionAnalysis analyzeFunction(
        const std::string& expression,
        double lower,
        double upper
    );
    static ScalarToolResult averageValue(
        const std::string& expression,
        double lower,
        double upper
    );
    static std::vector<double> areaBreakdown(
        const std::string& expression,
        double lower,
        double upper
    );
    static ScalarToolResult arcLength(
        const std::string& expression,
        double lower,
        double upper
    );
    static ScalarToolResult revolutionVolume(
        const std::string& expression,
        double lower,
        double upper,
        char axis
    );
    static std::string fourierSeries(
        const std::string& expression,
        double period,
        int terms
    );
    static std::string laplaceTransform(const std::string& expression);
    static std::string solveOde(const std::string& equation);
    static std::vector<NumericTableRow> errorProfile(
        const std::string& expression,
        double lower,
        double upper
    );
    static ScalarToolResult doubleIntegral(
        const std::string& expression,
        double xLower,
        double xUpper,
        double yLower,
        double yUpper
    );
    static ScalarToolResult variableDoubleIntegral(
        const std::string& expression,
        double xLower,
        double xUpper,
        const std::string& yLower,
        const std::string& yUpper
    );
    static ScalarToolResult polarDoubleIntegral(
        const std::string& expression,
        double rLower,
        double rUpper,
        double thetaLower,
        double thetaUpper
    );
    static ScalarToolResult tripleIntegral(
        const std::string& expression,
        double xLower,
        double xUpper,
        double yLower,
        double yUpper,
        double zLower,
        double zUpper
    );
    static std::vector<NumericTableRow> parameterSensitivity(
        const std::string& expression,
        const std::string& parameter,
        const std::vector<double>& values,
        double lower,
        double upper
    );
    static bool verifyAntiderivative(
        const std::string& expression,
        const std::string& antiderivative,
        double* maximumError = nullptr
    );
    static std::string buildPiecewise(
        const std::vector<std::pair<std::string, std::string>>& pieces
    );
    static std::string parameterAssignment(const std::string& name, double value);
    static std::string substitutionHelp(
        const std::string& expression,
        const std::string& substitution
    );
    static std::string integrationByPartsHelp(
        const std::string& u,
        const std::string& dv
    );
};

}  // namespace calculator
