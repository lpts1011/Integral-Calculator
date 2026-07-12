#include "calculator/MathToolsDialog.hpp"

#include "calculator/ExpressionEngine.hpp"
#include "calculator/MathExtensions.hpp"

#include <QComboBox>
#include <QFormLayout>
#include <QLabel>
#include <QLineEdit>
#include <QMessageBox>
#include <QPushButton>
#include <QTabWidget>
#include <QTextEdit>
#include <QVBoxLayout>

#include <cmath>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace calculator {
namespace {

using Fields = std::vector<std::pair<QString, QString>>;
using ToolAction = std::function<QString(const std::vector<QString>&)>;

double number(const QString& text) {
    return ExpressionEngine::parseConstant(text.trimmed().toStdString());
}

int integer(const QString& text) {
    return static_cast<int>(std::llround(number(text)));
}

std::vector<double> numberList(QString text) {
    text.replace(';', ',');
    std::vector<double> values;
    for (const auto& item : text.split(',', Qt::SkipEmptyParts)) values.push_back(number(item));
    if (values.empty()) throw std::invalid_argument("Enter at least one value.");
    return values;
}

std::vector<int> integerList(QString text) {
    std::vector<int> values;
    for (double value : numberList(std::move(text))) values.push_back(static_cast<int>(std::llround(value)));
    return values;
}

QString scalarText(const ScalarToolResult& result) {
    return QStringLiteral("Exact / simplified: %1\nNumeric: %2\n%3")
        .arg(QString::fromStdString(result.exact))
        .arg(result.numeric, 0, 'g', 13)
        .arg(QString::fromStdString(result.details));
}

QString valuesText(const std::vector<double>& values) {
    QStringList items;
    for (double value : values) items << QString::number(value, 'g', 10);
    return items.isEmpty() ? QStringLiteral("none") : items.join(", ");
}

QString tableText(
    const std::vector<NumericTableRow>& rows,
    const QStringList& headings
) {
    QString text = headings.join("\t") + "\n";
    for (const auto& row : rows) {
        text += QString::fromStdString(row.label);
        for (double value : row.values) text += "\t" + QString::number(value, 'g', 11);
        text += "\n";
    }
    return text;
}

QWidget* toolPage(
    const Fields& definitions,
    const QString& buttonText,
    ToolAction action,
    QWidget* parent
) {
    auto* page = new QWidget(parent);
    auto* layout = new QVBoxLayout(page);
    auto* form = new QFormLayout;
    std::vector<QLineEdit*> fields;
    fields.reserve(definitions.size());
    for (const auto& [label, initial] : definitions) {
        auto* edit = new QLineEdit(initial);
        form->addRow(label, edit);
        fields.push_back(edit);
    }
    layout->addLayout(form);
    auto* button = new QPushButton(buttonText);
    auto* output = new QTextEdit;
    output->setReadOnly(true);
    output->setMinimumHeight(150);
    layout->addWidget(button);
    layout->addWidget(output, 1);
    QObject::connect(button, &QPushButton::clicked, page, [fields, output, action] {
        std::vector<QString> values;
        values.reserve(fields.size());
        for (auto* field : fields) values.push_back(field->text().trimmed());
        try {
            output->setPlainText(action(values));
        } catch (const std::exception& error) {
            QMessageBox::critical(output, QObject::tr("Error"), QString::fromUtf8(error.what()));
        }
    });
    return page;
}

}  // namespace

MathToolsDialog::MathToolsDialog(
    InsertHandler insertFunction,
    InsertHandler insertParameter,
    QWidget* parent
) : QDialog(parent),
    insertFunction_(std::move(insertFunction)),
    insertParameter_(std::move(insertParameter)) {
    setWindowTitle(tr("Mathematical Tools"));
    resize(850, 620);
    auto* layout = new QVBoxLayout(this);
    tabs_ = new QTabWidget;
    tabs_->setDocumentMode(true);
    layout->addWidget(tabs_);
    buildTools();
}

void MathToolsDialog::buildTools() {
    tabs_->addTab(toolPage({
        {tr("Radius r(theta):"), "2*cos(theta)"}, {tr("Lower:"), "-pi/2"}, {tr("Upper:"), "pi/2"}
    }, tr("Compute Polar Area"), [](const auto& v) {
        return scalarText(MathExtensions::polarArea(v[0].toStdString(), number(v[1]), number(v[2])));
    }, this), tr("Polar Area"));

    tabs_->addTab(toolPage({
        {tr("Function:"), "sin(x)"}, {tr("Expansion point:"), "0"}, {tr("Order:"), "5"}
    }, tr("Build Taylor Polynomial"), [](const auto& v) {
        return QString::fromStdString(MathExtensions::taylorPolynomial(v[0].toStdString(), number(v[1]), integer(v[2])));
    }, this), tr("Taylor"));

    tabs_->addTab(toolPage({
        {tr("Function:"), "x^2"}, {tr("Lower:"), "0"}, {tr("Upper:"), "1"},
        {tr("Method:"), "Trapezoidal"}, {tr("Intervals:"), "20,50,100,200"}
    }, tr("Build Table"), [](const auto& v) {
        return tableText(MathExtensions::convergenceTable(
            v[0].toStdString(), number(v[1]), number(v[2]), v[3].toStdString(), integerList(v[4])
        ), {"n", "delta", "value", "absolute error"});
    }, this), tr("Convergence Table"));

    tabs_->addTab(toolPage({
        {tr("Function:"), "x^2-1"}, {tr("Lower:"), "-2"}, {tr("Upper:"), "2"}
    }, tr("Analyze Function"), [](const auto& v) {
        const auto result = MathExtensions::analyzeFunction(v[0].toStdString(), number(v[1]), number(v[2]));
        return QStringLiteral("Roots: %1\nCritical points: %2\nInflection points: %3\nSingularities: %4")
            .arg(valuesText(result.roots), valuesText(result.criticalPoints),
                 valuesText(result.inflectionPoints), valuesText(result.singularities));
    }, this), tr("Analysis"));

    tabs_->addTab(toolPage({
        {tr("Expression 1:"), "x"}, {tr("Condition 1:"), "x < 0"},
        {tr("Expression 2:"), "x^2"}, {tr("Condition 2:"), "True"}
    }, tr("Build and Insert Piecewise"), [this](const auto& v) {
        const QString result = QString::fromStdString(MathExtensions::buildPiecewise({
            {v[0].toStdString(), v[1].toStdString()}, {v[2].toStdString(), v[3].toStdString()}
        }));
        insertFunction_(result);
        return tr("Inserted into the current tab:\n") + result;
    }, this), tr("Piecewise Builder"));

    tabs_->addTab(toolPage({
        {tr("Parameter name:"), "a"}, {tr("Value:"), "1"}
    }, tr("Apply Value"), [this](const auto& v) {
        const QString result = QString::fromStdString(MathExtensions::parameterAssignment(v[0].toStdString(), number(v[1])));
        insertParameter_(result);
        return tr("Applied parameter: ") + result;
    }, this), tr("Parameter"));

    tabs_->addTab(toolPage({
        {tr("Function:"), "x"}, {tr("Lower:"), "-1"}, {tr("Upper:"), "1"}
    }, tr("Compute Average and Area"), [](const auto& v) {
        const auto average = MathExtensions::averageValue(v[0].toStdString(), number(v[1]), number(v[2]));
        const auto area = MathExtensions::areaBreakdown(v[0].toStdString(), number(v[1]), number(v[2]));
        return scalarText(average) + QStringLiteral("\nSigned area: %1\nAbsolute area: %2\nPositive: %3\nNegative: %4")
            .arg(area[0], 0, 'g', 10).arg(area[1], 0, 'g', 10).arg(area[2], 0, 'g', 10).arg(area[3], 0, 'g', 10);
    }, this), tr("Average / Area"));

    tabs_->addTab(toolPage({
        {tr("Integrand:"), "2*x*cos(x^2)"}, {tr("Substitution:"), "u=x^2"},
        {tr("u for parts:"), "x"}, {tr("dv for parts:"), "exp(x)"}
    }, tr("Show Techniques"), [](const auto& v) {
        return QString::fromStdString(MathExtensions::substitutionHelp(v[0].toStdString(), v[1].toStdString()) + "\n\n" +
            MathExtensions::integrationByPartsHelp(v[2].toStdString(), v[3].toStdString()));
    }, this), tr("Techniques"));

    tabs_->addTab(toolPage({
        {tr("Function:"), "x"}, {tr("Lower:"), "0"}, {tr("Upper:"), "1"}, {tr("Axis (x/y):"), "x"}
    }, tr("Compute Geometry"), [](const auto& v) {
        const auto arc = MathExtensions::arcLength(v[0].toStdString(), number(v[1]), number(v[2]));
        const char axis = v[3].trimmed().toLower() == "y" ? 'y' : 'x';
        const auto volume = MathExtensions::revolutionVolume(v[0].toStdString(), number(v[1]), number(v[2]), axis);
        return tr("Arc length\n") + scalarText(arc) + tr("\n\nVolume of revolution\n") + scalarText(volume);
    }, this), tr("Geometry"));

    tabs_->addTab(toolPage({
        {tr("Function:"), "x"}, {tr("Period:"), "2*pi"}, {tr("Terms:"), "5"},
        {tr("ODE:"), "y' = x*y"}
    }, tr("Compute Transforms and ODE"), [](const auto& v) {
        return QStringLiteral("Fourier: %1\n\nLaplace: %2\n\nODE: %3")
            .arg(QString::fromStdString(MathExtensions::fourierSeries(v[0].toStdString(), number(v[1]), integer(v[2]))),
                 QString::fromStdString(MathExtensions::laplaceTransform(v[0].toStdString())),
                 QString::fromStdString(MathExtensions::solveOde(v[3].toStdString())));
    }, this), tr("Transforms / ODE"));

    tabs_->addTab(toolPage({
        {tr("Function:"), "x^2"}, {tr("Lower:"), "0"}, {tr("Upper:"), "1"}
    }, tr("Build Error Profile"), [](const auto& v) {
        return tableText(MathExtensions::errorProfile(v[0].toStdString(), number(v[1]), number(v[2])),
                         {"method", "value", "absolute error", "estimate"});
    }, this), tr("Error Profile"));

    tabs_->addTab(toolPage({
        {tr("Function f(x,y):"), "x+y"}, {tr("x lower:"), "0"}, {tr("x upper:"), "1"},
        {tr("y lower:"), "0"}, {tr("y upper:"), "1"}
    }, tr("Compute Double Integral"), [](const auto& v) {
        return scalarText(MathExtensions::doubleIntegral(
            v[0].toStdString(), number(v[1]), number(v[2]), number(v[3]), number(v[4])
        ));
    }, this), tr("Double Integral"));

    tabs_->addTab(toolPage({
        {tr("Variable-bound f(x,y):"), "1"}, {tr("x lower:"), "0"}, {tr("x upper:"), "1"},
        {tr("y lower(x):"), "0"}, {tr("y upper(x):"), "x"},
        {tr("Polar f(r,theta):"), "1"}, {tr("r lower:"), "0"}, {tr("r upper:"), "1"},
        {tr("theta lower:"), "0"}, {tr("theta upper:"), "2*pi"}
    }, tr("Compute More Integrals"), [](const auto& v) {
        const auto variable = MathExtensions::variableDoubleIntegral(
            v[0].toStdString(), number(v[1]), number(v[2]), v[3].toStdString(), v[4].toStdString()
        );
        const auto polar = MathExtensions::polarDoubleIntegral(
            v[5].toStdString(), number(v[6]), number(v[7]), number(v[8]), number(v[9])
        );
        return tr("Variable-bound double integral\n") + scalarText(variable) +
               tr("\n\nPolar double integral\n") + scalarText(polar);
    }, this), tr("More Integrals"));

    tabs_->addTab(toolPage({
        {tr("Triple f(x,y,z):"), "1"}, {tr("x lower:"), "0"}, {tr("x upper:"), "1"},
        {tr("y lower:"), "0"}, {tr("y upper:"), "1"}, {tr("z lower:"), "0"}, {tr("z upper:"), "1"}
    }, tr("Compute Triple Integral"), [](const auto& v) {
        return scalarText(MathExtensions::tripleIntegral(
            v[0].toStdString(), number(v[1]), number(v[2]), number(v[3]),
            number(v[4]), number(v[5]), number(v[6])
        ));
    }, this), tr("Triple Integral"));

    tabs_->addTab(toolPage({
        {tr("Function with parameter:"), "a*x"}, {tr("Parameter:"), "a"},
        {tr("Values:"), "1,2,3"}, {tr("Lower:"), "0"}, {tr("Upper:"), "1"},
        {tr("Antiderivative candidate:"), "a*x^2/2"}
    }, tr("Analyze Sensitivity"), [](const auto& v) {
        const auto rows = MathExtensions::parameterSensitivity(
            v[0].toStdString(), v[1].toStdString(), numberList(v[2]), number(v[3]), number(v[4])
        );
        QString result = tableText(rows, {"parameter", "integral"});
        try {
            const auto parameterMap = ExpressionEngine::parseParameters(
                MathExtensions::parameterAssignment(v[1].toStdString(), numberList(v[2]).front())
            );
            const auto function = ExpressionEngine::substituteParameters(v[0].toStdString(), parameterMap);
            const auto candidate = ExpressionEngine::substituteParameters(v[5].toStdString(), parameterMap);
            double error = 0.0;
            const bool ok = MathExtensions::verifyAntiderivative(function, candidate, &error);
            result += QStringLiteral("\nVerification: %1 (maximum sampled error %2)")
                .arg(ok ? QObject::tr("passed") : QObject::tr("failed"))
                .arg(error, 0, 'g', 8);
        } catch (...) {
        }
        return result;
    }, this), tr("Sensitivity"));
}

}  // namespace calculator
