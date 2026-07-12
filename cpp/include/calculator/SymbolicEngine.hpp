#pragma once

#include <optional>
#include <string>

namespace calculator {

struct SymbolicResult {
    bool closedForm = false;
    std::string expression;
};

class SymbolicEngine {
public:
    static SymbolicResult antiderivative(const std::string& expression);
    static std::optional<double> definiteIntegral(
        const std::string& expression,
        double lower,
        double upper
    );
};

}  // namespace calculator

