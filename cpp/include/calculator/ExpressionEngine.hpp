#pragma once

#include <map>
#include <string>
#include <vector>

#include <muParser.h>

namespace calculator {

using ParameterMap = std::map<std::string, double>;

class ExpressionEngine {
public:
    explicit ExpressionEngine(std::string expression, ParameterMap parameters = {});

    double evaluate(double x) const;
    const std::string& expression() const noexcept;

    static ParameterMap parseParameters(const std::string& text);
    static double parseConstant(const std::string& text);
    static std::string normalize(std::string expression);
    static std::string substituteParameters(
        std::string expression,
        const ParameterMap& parameters
    );

private:
    std::string expression_;
    ParameterMap parameters_;
    mutable double x_ = 0.0;
    mutable mu::Parser parser_;

    void configureParser();
};

class VariableExpressionEngine {
public:
    explicit VariableExpressionEngine(
        std::string expression,
        std::vector<std::string> variableNames,
        ParameterMap constants = {}
    );

    void setVariable(const std::string& name, double value);
    double evaluate() const;

private:
    std::string expression_;
    mutable std::map<std::string, double> variables_;
    ParameterMap constants_;
    mutable mu::Parser parser_;
};

}  // namespace calculator
