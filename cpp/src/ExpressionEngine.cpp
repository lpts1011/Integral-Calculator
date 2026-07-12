#include "calculator/ExpressionEngine.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>
#include <regex>
#include <iomanip>
#include <sstream>
#include <stdexcept>

namespace calculator {
namespace {

std::string trim(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) {
        return {};
    }
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

double signFunction(double value) {
    return (value > 0.0) - (value < 0.0);
}

}  // namespace

ExpressionEngine::ExpressionEngine(std::string expression, ParameterMap parameters)
    : expression_(normalize(std::move(expression))), parameters_(std::move(parameters)) {
    if (expression_.empty()) {
        throw std::invalid_argument("Expression cannot be empty.");
    }
    configureParser();
}

void ExpressionEngine::configureParser() {
    parser_.DefineVar("x", &x_);
    parser_.DefineConst("pi", std::numbers::pi);
    parser_.DefineConst("e", std::numbers::e);
    parser_.DefineConst("E", std::numbers::e);
    parser_.DefineFun("sign", signFunction);
    for (const auto& [name, value] : parameters_) {
        parser_.DefineConst(name, value);
    }
    parser_.SetExpr(expression_);
}

double ExpressionEngine::evaluate(double x) const {
    x_ = x;
    try {
        const double value = parser_.Eval();
        if (!std::isfinite(value)) {
            throw std::runtime_error("Expression produced a non-finite value.");
        }
        return value;
    } catch (const mu::Parser::exception_type& error) {
        throw std::runtime_error(error.GetMsg());
    }
}

const std::string& ExpressionEngine::expression() const noexcept {
    return expression_;
}

ParameterMap ExpressionEngine::parseParameters(const std::string& text) {
    ParameterMap result;
    std::string normalized = text;
    std::replace(normalized.begin(), normalized.end(), ';', ',');
    std::stringstream stream(normalized);
    std::string item;
    const std::regex namePattern(R"(^[A-Za-z_][A-Za-z0-9_]*$)");

    while (std::getline(stream, item, ',')) {
        item = trim(item);
        if (item.empty()) {
            continue;
        }
        const auto separator = item.find('=');
        if (separator == std::string::npos) {
            throw std::invalid_argument("Parameters must use name=value format.");
        }
        const std::string name = trim(item.substr(0, separator));
        const std::string valueText = trim(item.substr(separator + 1));
        if (!std::regex_match(name, namePattern) || name == "x" || name == "pi" || name == "e") {
            throw std::invalid_argument("Invalid or reserved parameter name: " + name);
        }
        if (result.contains(name)) {
            throw std::invalid_argument("Duplicate parameter: " + name);
        }
        result.emplace(name, parseConstant(valueText));
    }
    return result;
}

double ExpressionEngine::parseConstant(const std::string& text) {
    mu::Parser parser;
    parser.DefineConst("pi", std::numbers::pi);
    parser.DefineConst("e", std::numbers::e);
    parser.DefineConst("E", std::numbers::e);
    try {
        parser.SetExpr(normalize(text));
        const double value = parser.Eval();
        if (!std::isfinite(value)) {
            throw std::invalid_argument("Value must be finite.");
        }
        return value;
    } catch (const mu::Parser::exception_type& error) {
        throw std::invalid_argument(error.GetMsg());
    }
}

std::string ExpressionEngine::normalize(std::string expression) {
    expression = trim(expression);
    for (std::size_t position = 0; (position = expression.find("**", position)) != std::string::npos;) {
        expression.replace(position, 2, "^");
    }
    expression = std::regex_replace(expression, std::regex(R"(\bln\s*\()"), "log(");
    expression = std::regex_replace(
        expression,
        std::regex(R"((\d|\))\s*(x|y|z|r|theta|t|s|u|pi|e)\b)"),
        "$1*$2"
    );
    expression = std::regex_replace(
        expression,
        std::regex(R"((\b(?:x|y|z|r|theta|t|s|u)\b|\))\s*\()"),
        "$1*("
    );
    expression = std::regex_replace(expression, std::regex(R"(\)\s*\()"), ")*(");
    return expression;
}

std::string ExpressionEngine::substituteParameters(
    std::string expression,
    const ParameterMap& parameters
) {
    for (const auto& [name, value] : parameters) {
        std::ostringstream number;
        number << std::setprecision(17) << value;
        expression = std::regex_replace(
            expression,
            std::regex("\\b" + name + "\\b"),
            number.str()
        );
    }
    return expression;
}

VariableExpressionEngine::VariableExpressionEngine(
    std::string expression,
    std::vector<std::string> variableNames,
    ParameterMap constants
) : expression_(ExpressionEngine::normalize(std::move(expression))), constants_(std::move(constants)) {
    if (expression_.empty()) {
        throw std::invalid_argument("Expression cannot be empty.");
    }
    for (const auto& name : variableNames) {
        if (name.empty() || variables_.contains(name)) {
            throw std::invalid_argument("Variable names must be non-empty and unique.");
        }
        variables_.emplace(name, 0.0);
    }
    for (auto& [name, value] : variables_) {
        parser_.DefineVar(name, &value);
    }
    parser_.DefineConst("pi", std::numbers::pi);
    parser_.DefineConst("e", std::numbers::e);
    parser_.DefineConst("E", std::numbers::e);
    parser_.DefineFun("sign", signFunction);
    for (const auto& [name, value] : constants_) {
        if (variables_.contains(name)) {
            throw std::invalid_argument("A constant cannot reuse a variable name: " + name);
        }
        parser_.DefineConst(name, value);
    }
    parser_.SetExpr(expression_);
}

void VariableExpressionEngine::setVariable(const std::string& name, double value) {
    const auto iterator = variables_.find(name);
    if (iterator == variables_.end()) {
        throw std::invalid_argument("Unknown variable: " + name);
    }
    iterator->second = value;
}

double VariableExpressionEngine::evaluate() const {
    try {
        const double value = parser_.Eval();
        if (!std::isfinite(value)) {
            throw std::runtime_error("Expression produced a non-finite value.");
        }
        return value;
    } catch (const mu::Parser::exception_type& error) {
        throw std::runtime_error(error.GetMsg());
    }
}

}  // namespace calculator
