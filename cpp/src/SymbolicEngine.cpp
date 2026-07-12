#include "calculator/SymbolicEngine.hpp"

#include "calculator/ExpressionEngine.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <iomanip>
#include <regex>
#include <sstream>
#include <vector>

namespace calculator {
namespace {

std::string compact(std::string value) {
    value.erase(std::remove_if(value.begin(), value.end(), [](unsigned char character) {
        return std::isspace(character) != 0;
    }), value.end());
    return value;
}

std::string numberText(double value) {
    std::ostringstream stream;
    stream << std::setprecision(14) << value;
    return stream.str();
}

double coefficientValue(const std::string& text) {
    if (text.empty() || text == "+") {
        return 1.0;
    }
    if (text == "-") {
        return -1.0;
    }
    return std::stod(text);
}

std::vector<std::string> splitTerms(const std::string& expression) {
    std::vector<std::string> terms;
    int depth = 0;
    std::size_t start = 0;
    for (std::size_t index = 0; index < expression.size(); ++index) {
        const char character = expression[index];
        if (character == '(') {
            ++depth;
        } else if (character == ')') {
            --depth;
        } else if (depth == 0 && index > start && (character == '+' || character == '-')) {
            terms.push_back(expression.substr(start, index - start));
            start = index;
        }
    }
    terms.push_back(expression.substr(start));
    return terms;
}

SymbolicResult integrateSingleTerm(const std::string& term) {
    if (term == "x" || term == "+x") {
        return {true, "x^2/2"};
    }
    if (term == "-x") {
        return {true, "-x^2/2"};
    }
    if (term == "1/x" || term == "x^-1") {
        return {true, "log(abs(x))"};
    }
    if (term == "-1/x" || term == "-x^-1") {
        return {true, "-log(abs(x))"};
    }

    std::smatch match;
    const std::regex powerPattern(R"(^([+-]?(?:\d+(?:\.\d*)?|\.\d+)?)\*?x\^([+-]?(?:\d+(?:\.\d*)?|\.\d+))$)");
    if (std::regex_match(term, match, powerPattern)) {
        const double coefficient = coefficientValue(match[1].str());
        const double power = std::stod(match[2].str());
        if (std::abs(power + 1.0) < 1e-12) {
            return {true, numberText(coefficient) + "*log(abs(x))"};
        }
        const double nextPower = power + 1.0;
        return {
            true,
            numberText(coefficient / nextPower) + "*x^" + numberText(nextPower)
        };
    }

    const std::regex linearPattern(R"(^([+-]?(?:\d+(?:\.\d*)?|\.\d+))\*?x$)");
    if (std::regex_match(term, match, linearPattern)) {
        return {true, numberText(std::stod(match[1].str()) / 2.0) + "*x^2"};
    }

    const std::regex functionPattern(
        R"(^([+-]?(?:\d+(?:\.\d*)?|\.\d+)?)\*?(sin|cos|exp)\(([+-]?(?:\d+(?:\.\d*)?|\.\d+)?)\*?x\)$)"
    );
    if (std::regex_match(term, match, functionPattern)) {
        const double outer = coefficientValue(match[1].str());
        const double inner = coefficientValue(match[3].str());
        if (std::abs(inner) < 1e-15) {
            return {};
        }
        const std::string argument = numberText(inner) + "*x";
        if (match[2].str() == "sin") {
            return {true, numberText(-outer / inner) + "*cos(" + argument + ")"};
        }
        if (match[2].str() == "cos") {
            return {true, numberText(outer / inner) + "*sin(" + argument + ")"};
        }
        return {true, numberText(outer / inner) + "*exp(" + argument + ")"};
    }

    try {
        const double constant = ExpressionEngine::parseConstant(term);
        return {true, numberText(constant) + "*x"};
    } catch (...) {
        return {};
    }
}

}  // namespace

SymbolicResult SymbolicEngine::antiderivative(const std::string& expression) {
    const std::string normalized = compact(ExpressionEngine::normalize(expression));
    const auto terms = splitTerms(normalized);
    std::string combined;
    for (const auto& term : terms) {
        const auto result = integrateSingleTerm(term);
        if (!result.closedForm) {
            return {};
        }
        if (!combined.empty() && !result.expression.starts_with('-')) {
            combined += "+";
        }
        combined += result.expression;
    }
    return {!combined.empty(), combined};
}

std::optional<double> SymbolicEngine::definiteIntegral(
    const std::string& expression,
    double lower,
    double upper
) {
    const auto result = antiderivative(expression);
    if (!result.closedForm) {
        return std::nullopt;
    }
    try {
        ExpressionEngine antiderivative(result.expression);
        return antiderivative.evaluate(upper) - antiderivative.evaluate(lower);
    } catch (...) {
        return std::nullopt;
    }
}

}  // namespace calculator
