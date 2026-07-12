#include "calculator/MainWindow.hpp"

#include "calculator/ExpressionEngine.hpp"
#include "calculator/IntegralPreviewWidget.hpp"
#include "calculator/MathToolsDialog.hpp"
#include "calculator/NumericalIntegrator.hpp"
#include "calculator/PlotWidget.hpp"
#include "calculator/SymbolicEngine.hpp"

#include <QApplication>
#include <QClipboard>
#include <QComboBox>
#include <QDialog>
#include <QFile>
#include <QFileDialog>
#include <QFormLayout>
#include <QFutureWatcher>
#include <QGridLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMap>
#include <QMessageBox>
#include <QProgressBar>
#include <QPushButton>
#include <QRegularExpression>
#include <QSettings>
#include <QSplitter>
#include <QTableWidget>
#include <QTabWidget>
#include <QTextStream>
#include <QVBoxLayout>
#include <QtConcurrent>

#include <algorithm>
#include <cmath>
#include <limits>

namespace calculator {
namespace {

QString formatNumber(double value, int precision = 12) {
    return QString::number(value, 'g', precision);
}

QString normalizedText(QLineEdit* edit) {
    return edit->text().trimmed();
}

std::vector<double> parseSplitPoints(const QString& text, double lower, double upper) {
    std::vector<double> points;
    QString normalized = text;
    normalized.replace(';', ',');
    for (const auto& part : normalized.split(',', Qt::SkipEmptyParts)) {
        const double point = ExpressionEngine::parseConstant(part.trimmed().toStdString());
        const double minimum = std::min(lower, upper);
        const double maximum = std::max(lower, upper);
        if (point > minimum && point < maximum) {
            points.push_back(point);
        }
    }
    std::sort(points.begin(), points.end());
    points.erase(std::unique(points.begin(), points.end()), points.end());
    if (lower > upper) {
        std::reverse(points.begin(), points.end());
    }
    return points;
}

IntegrationResult integrateSegments(
    const std::string& method,
    const NumericalIntegrator::Function& function,
    double lower,
    double upper,
    double delta,
    const std::vector<double>& splitPoints
) {
    std::vector<double> boundaries{lower};
    boundaries.insert(boundaries.end(), splitPoints.begin(), splitPoints.end());
    boundaries.push_back(upper);
    IntegrationResult combined;
    double squaredError = 0.0;
    for (std::size_t index = 0; index + 1 < boundaries.size(); ++index) {
        const auto segment = NumericalIntegrator::integrate(
            method, function, boundaries[index], boundaries[index + 1], delta
        );
        combined.value += segment.value;
        if (segment.hasErrorEstimate) {
            combined.hasErrorEstimate = true;
            squaredError += segment.errorEstimate * segment.errorEstimate;
        }
    }
    combined.errorEstimate = std::sqrt(squaredError);
    return combined;
}

}  // namespace

MainWindow::MainWindow(QWidget* parent) : QMainWindow(parent) {
    buildInterface();
    applyTheme(QStringLiteral("Light"));
    resize(1180, 760);
    setWindowTitle(QStringLiteral("Integral Calculator C++"));
}

void MainWindow::buildInterface() {
    auto* central = new QWidget(this);
    auto* rootLayout = new QVBoxLayout(central);
    rootLayout->setContentsMargins(12, 10, 12, 10);

    auto* toolbar = new QHBoxLayout;
    language_ = new QComboBox;
    language_->addItems({
        "English", "简体中文", "繁體中文", "Español", "Français",
        "日本語", "한국어", "العربية", "हिन्दी"
    });
    theme_ = new QComboBox;
    theme_->addItems({"Light", "Dark"});
    auto* reset = new QPushButton(tr("Reset"));
    auto* exportButton = new QPushButton(tr("Export"));
    auto* stepsButton = new QPushButton(tr("Steps"));
    auto* suggestionsButton = new QPushButton(tr("Suggestions"));
    auto* toolsButton = new QPushButton(tr("Math Tools"));
    auto* usageButton = new QPushButton(tr("Usage Instructions"));
    favorites_ = new QComboBox;
    favorites_->setMinimumWidth(150);
    favorites_->addItems(QSettings().value("favorites").toStringList());
    auto* insertFavoriteButton = new QPushButton(tr("Insert"));
    auto* addFavoriteButton = new QPushButton(tr("Add Current"));
    toolbar->addWidget(new QLabel(tr("Language:")));
    toolbar->addWidget(language_);
    toolbar->addWidget(new QLabel(tr("Theme:")));
    toolbar->addWidget(theme_);
    toolbar->addWidget(usageButton);
    toolbar->addWidget(new QLabel(tr("Favorite:")));
    toolbar->addWidget(favorites_);
    toolbar->addWidget(insertFavoriteButton);
    toolbar->addWidget(addFavoriteButton);
    toolbar->addStretch();
    rootLayout->addLayout(toolbar);

    auto* toolsRow = new QHBoxLayout;
    templates_ = new QComboBox;
    templates_->addItem(tr("Polynomial"), "x^2");
    templates_->addItem(tr("Gaussian"), "exp(-x^2)");
    templates_->addItem(tr("Oscillatory"), "sin(x^2)");
    templates_->addItem(tr("Rational"), "1/(1+x^2)");
    templates_->addItem(tr("Exponential decay"), "exp(-x)");
    auto* insertTemplateButton = new QPushButton(tr("Insert Template"));
    toolsRow->addWidget(new QLabel(tr("Template:")));
    toolsRow->addWidget(templates_);
    toolsRow->addWidget(insertTemplateButton);
    toolsRow->addStretch();
    toolsRow->addWidget(suggestionsButton);
    toolsRow->addWidget(toolsButton);
    toolsRow->addWidget(stepsButton);
    toolsRow->addWidget(exportButton);
    toolsRow->addWidget(reset);
    rootLayout->addLayout(toolsRow);

    auto* splitter = new QSplitter(Qt::Horizontal);
    tabs_ = new QTabWidget;
    tabs_->addTab(buildBasicTab(), tr("Basic Integration"));
    tabs_->addTab(buildAdvancedTab(), tr("Advanced Integration"));
    tabs_->addTab(buildImproperTab(), tr("Improper Integral"));
    splitter->addWidget(tabs_);

    auto* rightPanel = new QWidget;
    auto* rightLayout = new QVBoxLayout(rightPanel);
    plot_ = new PlotWidget;
    history_ = new QListWidget;
    history_->setMinimumHeight(170);
    rightLayout->addWidget(plot_, 3);
    rightLayout->addWidget(new QLabel(tr("History")));
    rightLayout->addWidget(history_, 1);
    splitter->addWidget(rightPanel);
    splitter->setStretchFactor(0, 3);
    splitter->setStretchFactor(1, 2);
    rootLayout->addWidget(splitter, 1);

    progress_ = new QProgressBar;
    progress_->setRange(0, 0);
    progress_->hide();
    rootLayout->addWidget(progress_);
    setCentralWidget(central);

    connect(reset, &QPushButton::clicked, this, &MainWindow::resetAll);
    connect(exportButton, &QPushButton::clicked, this, &MainWindow::exportHistory);
    connect(stepsButton, &QPushButton::clicked, this, &MainWindow::showSteps);
    connect(suggestionsButton, &QPushButton::clicked, this, &MainWindow::showSuggestions);
    connect(toolsButton, &QPushButton::clicked, this, &MainWindow::showMathTools);
    connect(usageButton, &QPushButton::clicked, this, &MainWindow::showUsage);
    connect(insertFavoriteButton, &QPushButton::clicked, this, &MainWindow::insertFavorite);
    connect(addFavoriteButton, &QPushButton::clicked, this, &MainWindow::addFavorite);
    connect(insertTemplateButton, &QPushButton::clicked, this, &MainWindow::insertTemplate);
    connect(history_, &QListWidget::itemDoubleClicked, this, &MainWindow::refillFromHistory);
    connect(theme_, &QComboBox::currentTextChanged, this, &MainWindow::applyTheme);
    connect(language_, &QComboBox::currentTextChanged, this, &MainWindow::applyLanguage);
}

QWidget* MainWindow::buildBasicTab() {
    auto* page = new QWidget;
    auto* layout = new QVBoxLayout(page);

    auto* integralInput = new QGridLayout;
    auto* integralSymbol = new QLabel(QStringLiteral("∫"));
    QFont integralFont = integralSymbol->font();
    integralFont.setPointSize(56);
    integralSymbol->setFont(integralFont);
    integralSymbol->setAlignment(Qt::AlignCenter);

    basicFunction_ = new QLineEdit("sin(x)");
    basicParameters_ = new QLineEdit;
    basicLower_ = new QLineEdit("0");
    basicUpper_ = new QLineEdit("pi");
    basicLower_->setAlignment(Qt::AlignCenter);
    basicUpper_->setAlignment(Qt::AlignCenter);
    basicLower_->setMaximumWidth(150);
    basicUpper_->setMaximumWidth(150);
    basicFunction_->setMinimumWidth(280);

    auto* dx = new QLabel(QStringLiteral("dx"));
    QFont dxFont = dx->font();
    dxFont.setPointSize(24);
    dx->setFont(dxFont);

    integralInput->addWidget(integralSymbol, 0, 0, 2, 1);
    integralInput->addWidget(basicUpper_, 0, 1);
    integralInput->addWidget(basicLower_, 1, 1);
    integralInput->addWidget(basicFunction_, 0, 2, 2, 1);
    integralInput->addWidget(dx, 0, 3, 2, 1);
    integralInput->setColumnStretch(2, 1);
    layout->addLayout(integralInput);

    auto* parametersRow = new QHBoxLayout;
    parametersRow->addWidget(new QLabel(tr("Parameters:")));
    parametersRow->addWidget(basicParameters_, 1);
    layout->addLayout(parametersRow);

    basicPreview_ = new IntegralPreviewWidget;
    layout->addWidget(basicPreview_);

    basicCalculate_ = new QPushButton(tr("Calculate Integral"));
    basicCalculate_->setMinimumWidth(230);
    basicResult_ = new QLabel;
    basicResult_->setWordWrap(true);
    basicResult_->setAlignment(Qt::AlignCenter);
    basicExact_ = new QPushButton(tr("View Exact Result"));
    basicExact_->setMinimumWidth(230);
    auto* basicReset = new QPushButton(tr("Reset"));
    basicReset->setMinimumWidth(230);

    layout->addWidget(basicCalculate_, 0, Qt::AlignHCenter);
    layout->addWidget(basicResult_);
    layout->addStretch();
    layout->addWidget(basicExact_, 0, Qt::AlignHCenter);
    layout->addWidget(basicReset, 0, Qt::AlignHCenter);
    layout->addSpacing(18);

    connect(basicCalculate_, &QPushButton::clicked, this, &MainWindow::calculateBasic);
    connect(basicExact_, &QPushButton::clicked, this, &MainWindow::showBasicExactResult);
    connect(basicReset, &QPushButton::clicked, this, &MainWindow::resetAll);
    for (auto* edit : {basicFunction_, basicParameters_, basicLower_, basicUpper_}) {
        connect(edit, &QLineEdit::textChanged, this, &MainWindow::updateBasicPreview);
        connect(edit, &QLineEdit::returnPressed, this, &MainWindow::calculateBasic);
    }
    updateBasicPreview();
    return page;
}

QWidget* MainWindow::buildAdvancedTab() {
    auto* page = new QWidget;
    auto* layout = new QVBoxLayout(page);
    auto* form = new QFormLayout;
    advancedFunction_ = new QLineEdit("x^2");
    advancedParameters_ = new QLineEdit;
    advancedLower_ = new QLineEdit("0");
    advancedUpper_ = new QLineEdit("1");
    advancedSplit_ = new QLineEdit;
    advancedDelta_ = new QLineEdit;
    advancedMode_ = new QComboBox;
    advancedMode_->addItems({"Symbolic Integration", "Numerical Integration"});
    advancedMethod_ = new QComboBox;
    advancedMethod_->addItems({
        "Trapezoidal", "Simpson", "Rectangle", "Romberg",
        "Gaussian Quadrature", "Simpson 3/8", "Adaptive Simpson", "Monte Carlo"
    });
    form->addRow(tr("Function:"), advancedFunction_);
    form->addRow(tr("Parameters:"), advancedParameters_);
    form->addRow(tr("Lower limit:"), advancedLower_);
    form->addRow(tr("Upper limit:"), advancedUpper_);
    form->addRow(tr("Split points:"), advancedSplit_);
    form->addRow(tr("Step size:"), advancedDelta_);
    form->addRow(tr("Integration mode:"), advancedMode_);
    form->addRow(tr("Numerical method:"), advancedMethod_);
    layout->addLayout(form);
    advancedRecommendation_ = new QLabel;
    advancedRecommendation_->setWordWrap(true);
    applyRecommendation_ = new QPushButton(tr("Apply Recommendation"));
    layout->addWidget(advancedRecommendation_);
    layout->addWidget(applyRecommendation_, 0, Qt::AlignLeft);
    auto* actions = new QHBoxLayout;
    advancedCalculate_ = new QPushButton(tr("Calculate Integral"));
    compare_ = new QPushButton(tr("Compare Methods"));
    actions->addWidget(advancedCalculate_);
    actions->addWidget(compare_);
    layout->addLayout(actions);
    advancedResult_ = new QLabel;
    advancedResult_->setWordWrap(true);
    layout->addWidget(advancedResult_);
    layout->addStretch();
    connect(advancedCalculate_, &QPushButton::clicked, this, &MainWindow::calculateAdvanced);
    connect(compare_, &QPushButton::clicked, this, &MainWindow::compareMethods);
    connect(applyRecommendation_, &QPushButton::clicked, this, &MainWindow::applyAdvancedRecommendation);
    for (auto* edit : {advancedFunction_, advancedLower_, advancedUpper_}) {
        connect(edit, &QLineEdit::textChanged, this, &MainWindow::updateAdvancedRecommendation);
    }
    updateAdvancedRecommendation();
    return page;
}

QWidget* MainWindow::buildImproperTab() {
    auto* page = new QWidget;
    auto* layout = new QVBoxLayout(page);
    auto* form = new QFormLayout;
    improperFunction_ = new QLineEdit("exp(-x)");
    improperParameters_ = new QLineEdit;
    improperLower_ = new QLineEdit("0");
    improperUpper_ = new QLineEdit("inf");
    form->addRow(tr("Function:"), improperFunction_);
    form->addRow(tr("Parameters:"), improperParameters_);
    form->addRow(tr("Lower limit:"), improperLower_);
    form->addRow(tr("Upper limit:"), improperUpper_);
    layout->addLayout(form);
    improperCalculate_ = new QPushButton(tr("Compute Integral"));
    improperResult_ = new QLabel;
    improperResult_->setWordWrap(true);
    layout->addWidget(improperCalculate_);
    layout->addWidget(improperResult_);
    layout->addStretch();
    connect(improperCalculate_, &QPushButton::clicked, this, &MainWindow::calculateImproper);
    return page;
}

void MainWindow::calculateBasic() {
    const QString expression = normalizedText(basicFunction_);
    const QString parameters = normalizedText(basicParameters_);
    const QString lowerText = normalizedText(basicLower_);
    const QString upperText = normalizedText(basicUpper_);
    runTask([=] {
        CalculationOutput output;
        try {
            if (expression.isEmpty()) {
                throw std::invalid_argument("Function cannot be empty.");
            }
            if (lowerText.isEmpty() != upperText.isEmpty()) {
                throw std::invalid_argument("Provide both limits or leave both empty.");
            }
            const auto parameterMap = ExpressionEngine::parseParameters(parameters.toStdString());
            output.record = {
                {"tab", 0}, {"function", expression}, {"parameters", parameters},
                {"lower", lowerText}, {"upper", upperText}
            };
            const auto symbolicExpression = ExpressionEngine::substituteParameters(
                expression.toStdString(), parameterMap
            );
            if (lowerText.isEmpty()) {
                const auto symbolic = SymbolicEngine::antiderivative(symbolicExpression);
                if (!symbolic.closedForm) {
                    output.resultText = tr("No closed-form antiderivative is available yet.");
                    output.historyText = QStringLiteral("∫ %1 dx = no closed-form").arg(expression);
                    output.exactText = tr("No closed-form exact result was found.");
                } else {
                    output.resultText = QStringLiteral("%1 + C").arg(QString::fromStdString(symbolic.expression));
                    output.historyText = QStringLiteral("∫ %1 dx = %2 + C")
                        .arg(expression, QString::fromStdString(symbolic.expression));
                    output.exactText = QStringLiteral("Exact symbolic form:\n\n%1 + C")
                        .arg(QString::fromStdString(symbolic.expression));
                }
                output.success = true;
                return output;
            }
            const double lower = parseLimit(lowerText);
            const double upper = parseLimit(upperText);
            ExpressionEngine engine(expression.toStdString(), parameterMap);
            const auto function = [&engine](double x) { return engine.evaluate(x); };
            const auto numeric = NumericalIntegrator::integrate(
                "Adaptive Simpson", function, lower, upper
            );
            const auto exact = SymbolicEngine::definiteIntegral(symbolicExpression, lower, upper);
            output.resultText = exact
                ? QStringLiteral("Exact: %1    Numeric: %2").arg(formatNumber(*exact), formatNumber(numeric.value))
                : QStringLiteral("≈ %1").arg(formatNumber(numeric.value));
            output.exactText = exact
                ? QStringLiteral("Exact symbolic value:\n\n%1\n\nNumeric value:\n≈ %2")
                      .arg(formatNumber(*exact), formatNumber(numeric.value, 10))
                : QStringLiteral("No closed-form exact result was found.\n\nNumeric approximation:\n≈ %1")
                      .arg(formatNumber(numeric.value, 10));
            output.historyText = QStringLiteral("∫[%1, %2] %3 dx = %4")
                .arg(lowerText, upperText, expression, output.resultText);
            if (std::isfinite(lower) && std::isfinite(upper)) {
                output.plotPoints = sampleFunction(
                    expression.toStdString(), parameters.toStdString(), lower, upper
                );
            }
            output.success = true;
        } catch (const std::exception& error) {
            output.errorText = QString::fromUtf8(error.what());
        }
        return output;
    }, basicResult_);
}

void MainWindow::calculateAdvanced() {
    const QString expression = normalizedText(advancedFunction_);
    const QString parameters = normalizedText(advancedParameters_);
    const QString lowerText = normalizedText(advancedLower_);
    const QString upperText = normalizedText(advancedUpper_);
    const QString splitText = normalizedText(advancedSplit_);
    const QString deltaText = normalizedText(advancedDelta_);
    const QString mode = advancedMode_->currentText();
    const QString method = advancedMethod_->currentText();
    runTask([=] {
        CalculationOutput output;
        try {
            if (expression.isEmpty()) {
                throw std::invalid_argument("Function cannot be empty.");
            }
            if (lowerText.isEmpty() != upperText.isEmpty()) {
                throw std::invalid_argument("Provide both limits or leave both empty.");
            }
            const auto parameterMap = ExpressionEngine::parseParameters(parameters.toStdString());
            output.record = {
                {"tab", 1}, {"function", expression}, {"parameters", parameters},
                {"lower", lowerText}, {"upper", upperText}, {"split", splitText},
                {"delta", deltaText}, {"mode", mode}, {"method", method}
            };
            if (mode == "Symbolic Integration") {
                const auto symbolicExpression = ExpressionEngine::substituteParameters(
                    expression.toStdString(), parameterMap
                );
                if (lowerText.isEmpty()) {
                    const auto symbolic = SymbolicEngine::antiderivative(symbolicExpression);
                    output.resultText = symbolic.closedForm
                        ? QString::fromStdString(symbolic.expression) + " + C"
                        : tr("No closed-form antiderivative is available yet.");
                    output.historyText = QStringLiteral("Symbolic: ∫ %1 dx = %2")
                        .arg(expression, output.resultText);
                    output.success = true;
                    return output;
                }

                const double lower = parseLimit(lowerText);
                const double upper = parseLimit(upperText);
                ExpressionEngine engine(expression.toStdString(), parameterMap);
                const auto numeric = NumericalIntegrator::integrate(
                    "Adaptive Simpson",
                    [&engine](double x) { return engine.evaluate(x); },
                    lower,
                    upper
                );
                const auto exact = SymbolicEngine::definiteIntegral(symbolicExpression, lower, upper);
                output.resultText = exact
                    ? QStringLiteral("Exact: %1    Numeric: %2")
                          .arg(formatNumber(*exact), formatNumber(numeric.value))
                    : QStringLiteral("≈ %1").arg(formatNumber(numeric.value));
                output.historyText = QStringLiteral("Symbolic: ∫[%1, %2] %3 dx = %4")
                    .arg(lowerText, upperText, expression, output.resultText);
                if (std::isfinite(lower) && std::isfinite(upper)) {
                    output.plotPoints = sampleFunction(
                        expression.toStdString(), parameters.toStdString(), lower, upper
                    );
                }
                output.success = true;
                return output;
            }
            const double lower = parseLimit(lowerText);
            const double upper = parseLimit(upperText);
            const double delta = deltaText.isEmpty()
                ? 0.0
                : ExpressionEngine::parseConstant(deltaText.toStdString());
            ExpressionEngine engine(expression.toStdString(), parameterMap);
            const auto function = [&engine](double x) { return engine.evaluate(x); };
            const auto splitPoints = parseSplitPoints(splitText, lower, upper);
            const auto result = integrateSegments(
                method.toStdString(), function, lower, upper, delta, splitPoints
            );
            output.resultText = QStringLiteral("≈ %1").arg(formatNumber(result.value));
            if (result.hasErrorEstimate) {
                output.resultText += QStringLiteral("  (±%1)").arg(formatNumber(result.errorEstimate, 4));
            }
            output.historyText = QStringLiteral("%1: ∫[%2, %3] %4 dx = %5")
                .arg(method, lowerText, upperText, expression, output.resultText);
            if (std::isfinite(lower) && std::isfinite(upper)) {
                output.plotPoints = sampleFunction(
                    expression.toStdString(), parameters.toStdString(), lower, upper
                );
            }
            output.success = true;
        } catch (const std::exception& error) {
            output.errorText = QString::fromUtf8(error.what());
        }
        return output;
    }, advancedResult_);
}

void MainWindow::calculateImproper() {
    const QString expression = normalizedText(improperFunction_);
    const QString parameters = normalizedText(improperParameters_);
    const QString lowerText = normalizedText(improperLower_);
    const QString upperText = normalizedText(improperUpper_);
    runTask([=] {
        CalculationOutput output;
        try {
            const double lower = parseLimit(lowerText);
            const double upper = parseLimit(upperText);
            output.record = {
                {"tab", 2}, {"function", expression}, {"parameters", parameters},
                {"lower", lowerText}, {"upper", upperText}
            };
            const auto parameterMap = ExpressionEngine::parseParameters(parameters.toStdString());
            ExpressionEngine engine(expression.toStdString(), parameterMap);
            const auto result = NumericalIntegrator::integrate(
                "Adaptive Simpson",
                [&engine](double x) { return engine.evaluate(x); },
                lower,
                upper
            );
            output.resultText = QStringLiteral("≈ %1").arg(formatNumber(result.value));
            output.historyText = QStringLiteral("Improper: ∫[%1, %2] %3 dx = %4")
                .arg(lowerText, upperText, expression, output.resultText);
            output.success = true;
        } catch (const std::exception& error) {
            output.errorText = QString::fromUtf8(error.what());
        }
        return output;
    }, improperResult_);
}

void MainWindow::compareMethods() {
    const QString expression = normalizedText(advancedFunction_);
    const QString parameters = normalizedText(advancedParameters_);
    const QString lowerText = normalizedText(advancedLower_);
    const QString upperText = normalizedText(advancedUpper_);
    runTask([=] {
        CalculationOutput output;
        try {
            const double lower = parseLimit(lowerText);
            const double upper = parseLimit(upperText);
            if (!std::isfinite(lower) || !std::isfinite(upper)) {
                throw std::invalid_argument("Method comparison requires finite limits.");
            }
            const auto parameterMap = ExpressionEngine::parseParameters(parameters.toStdString());
            ExpressionEngine engine(expression.toStdString(), parameterMap);
            const auto function = [&engine](double x) { return engine.evaluate(x); };
            const QStringList methods = {
                "Rectangle", "Trapezoidal", "Simpson", "Simpson 3/8",
                "Romberg", "Gaussian Quadrature", "Adaptive Simpson", "Monte Carlo"
            };
            QStringList lines;
            for (const auto& method : methods) {
                const auto result = NumericalIntegrator::integrate(
                    method.toStdString(), function, lower, upper
                );
                lines << QStringLiteral("%1: %2").arg(method, formatNumber(result.value));
            }
            output.resultText = lines.join('\n');
            output.historyText = QStringLiteral("Comparison: %1 on [%2, %3]")
                .arg(expression, lowerText, upperText);
            output.success = true;
        } catch (const std::exception& error) {
            output.errorText = QString::fromUtf8(error.what());
        }
        return output;
    }, advancedResult_);
}

void MainWindow::runTask(std::function<CalculationOutput()> task, QLabel* targetLabel) {
    ++activeTasks_;
    progress_->show();
    targetLabel->setText(tr("Computing..."));
    basicCalculate_->setEnabled(false);
    advancedCalculate_->setEnabled(false);
    improperCalculate_->setEnabled(false);
    compare_->setEnabled(false);
    auto* watcher = new QFutureWatcher<CalculationOutput>(this);
    connect(watcher, &QFutureWatcher<CalculationOutput>::finished, this, [this, watcher, targetLabel] {
        const auto output = watcher->result();
        watcher->deleteLater();
        finishTask(output, targetLabel);
        --activeTasks_;
        if (activeTasks_ == 0) {
            progress_->hide();
            basicCalculate_->setEnabled(true);
            advancedCalculate_->setEnabled(true);
            improperCalculate_->setEnabled(true);
            compare_->setEnabled(true);
        }
    });
    watcher->setFuture(QtConcurrent::run(std::move(task)));
}

void MainWindow::finishTask(const CalculationOutput& output, QLabel* targetLabel) {
    if (!output.success) {
        targetLabel->clear();
        QMessageBox::critical(this, tr("Error"), output.errorText);
        return;
    }
    targetLabel->setText(output.resultText);
    if (targetLabel == basicResult_) {
        lastBasicExactText_ = output.exactText;
    }
    auto* item = new QListWidgetItem(output.historyText);
    item->setData(Qt::UserRole, output.record);
    history_->insertItem(0, item);
    lastSteps_ = output.historyText;
    if (!output.plotPoints.isEmpty()) {
        plot_->setSeries(output.plotPoints);
    }
}

double MainWindow::parseLimit(const QString& text) {
    const QString normalized = text.trimmed().toLower();
    if (normalized == "inf" || normalized == "+inf" || normalized == "oo" || normalized == "+oo") {
        return std::numeric_limits<double>::infinity();
    }
    if (normalized == "-inf" || normalized == "-oo") {
        return -std::numeric_limits<double>::infinity();
    }
    return ExpressionEngine::parseConstant(normalized.toStdString());
}

QVector<QPointF> MainWindow::sampleFunction(
    const std::string& expression,
    const std::string& parameters,
    double lower,
    double upper
) {
    ExpressionEngine engine(expression, ExpressionEngine::parseParameters(parameters));
    QVector<QPointF> points;
    points.reserve(600);
    for (int index = 0; index < 600; ++index) {
        const double x = lower + (upper - lower) * index / 599.0;
        try {
            points.append(QPointF(x, engine.evaluate(x)));
        } catch (...) {
            points.append(QPointF(x, std::numeric_limits<double>::quiet_NaN()));
        }
    }
    return points;
}

void MainWindow::resetAll() {
    for (auto* edit : {
             basicFunction_, basicParameters_, basicLower_, basicUpper_,
             advancedFunction_, advancedParameters_, advancedLower_, advancedUpper_,
             advancedSplit_, advancedDelta_, improperFunction_, improperParameters_,
             improperLower_, improperUpper_
         }) {
        edit->clear();
    }
    basicResult_->clear();
    advancedResult_->clear();
    improperResult_->clear();
    history_->clear();
    plot_->clearSeries();
    lastSteps_.clear();
    lastBasicExactText_.clear();
}

void MainWindow::showBasicExactResult() {
    QMessageBox::information(
        this,
        tr("Exact Result"),
        lastBasicExactText_.isEmpty() ? tr("No result to display.") : lastBasicExactText_
    );
}

void MainWindow::updateBasicPreview() {
    if (!basicPreview_) {
        return;
    }
    basicPreview_->setInput(
        basicFunction_->text(),
        basicParameters_->text(),
        basicLower_->text(),
        basicUpper_->text()
    );
}

void MainWindow::exportHistory() {
    if (history_->count() == 0) {
        QMessageBox::information(this, tr("Export"), tr("No calculation history is available."));
        return;
    }
    const QString path = QFileDialog::getSaveFileName(
        this, tr("Export History"), "integral-history.md",
        "Markdown (*.md);;LaTeX (*.tex);;Text (*.txt)"
    );
    if (path.isEmpty()) {
        return;
    }
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QMessageBox::critical(this, tr("Export"), tr("Unable to write the selected file."));
        return;
    }
    QTextStream stream(&file);
    if (path.endsWith(".tex", Qt::CaseInsensitive)) {
        stream << "\\documentclass{article}\n\\usepackage{amsmath}\n\\begin{document}\n";
        for (int index = 0; index < history_->count(); ++index) {
            QString value = history_->item(index)->text();
            value.replace("∫", "\\int ").replace("≈", "\\approx ");
            stream << "\\[\\text{" << value << "}\\]\n";
        }
        stream << "\\end{document}\n";
        return;
    }
    stream << "# Integral Calculator History\n\n";
    for (int index = 0; index < history_->count(); ++index) {
        stream << "- " << history_->item(index)->text() << '\n';
    }
}

void MainWindow::showSteps() {
    QMessageBox::information(
        this,
        tr("Steps"),
        lastSteps_.isEmpty()
            ? tr("Run a calculation first.")
            : tr("Calculation Steps\n\n1. Parse and validate the expression and parameters.\n"
                 "2. Resolve the integration interval and any split points.\n"
                 "3. Apply the selected symbolic or numerical method.\n"
                 "4. Validate and format the result.\n\n") + lastSteps_
    );
}

void MainWindow::showSuggestions() {
    QLineEdit* active = tabs_->currentIndex() == 0
        ? basicFunction_
        : (tabs_->currentIndex() == 1 ? advancedFunction_ : improperFunction_);
    const QString original = active->text();
    QString suggested = original.trimmed();
    suggested.replace(QRegularExpression("\\bsin([A-Za-z0-9_]+)\\b"), "sin(\\1)");
    suggested.replace(QRegularExpression("\\bcos([A-Za-z0-9_]+)\\b"), "cos(\\1)");
    suggested.replace(QRegularExpression("\\be\\^x\\b"), "exp(x)");
    suggested.replace(QRegularExpression("\\bx([0-9]+)\\b"), "x^\\1");
    const QString normalized = QString::fromStdString(ExpressionEngine::normalize(suggested.toStdString()));
    if (normalized != original) {
        active->setText(normalized);
    }
    QMessageBox::information(this, tr("Suggestions"), tr("Expression normalization has been applied."));
}

void MainWindow::showUsage() {
    QMessageBox::information(
        this,
        tr("Usage Instructions"),
        tr("Enter a function using x, for example sin(x), x^2, or exp(-x).\n"
           "Use name=value for parameters. Leave both limits empty for an indefinite integral.\n"
           "Advanced Integration provides symbolic and eight numerical methods.\n"
           "Double-click a history item to restore its inputs. Mathematical Tools contains "
           "analysis, transforms, geometry, and multiple-integral utilities.")
    );
}

void MainWindow::addFavorite() {
    QLineEdit* active = tabs_->currentIndex() == 0
        ? basicFunction_ : (tabs_->currentIndex() == 1 ? advancedFunction_ : improperFunction_);
    const QString value = active->text().trimmed();
    if (value.isEmpty()) return;
    if (favorites_->findText(value) < 0) favorites_->addItem(value);
    QStringList values;
    for (int index = 0; index < favorites_->count(); ++index) values << favorites_->itemText(index);
    QSettings().setValue("favorites", values);
    favorites_->setCurrentText(value);
}

void MainWindow::insertFavorite() {
    if (favorites_->currentText().isEmpty()) return;
    QLineEdit* active = tabs_->currentIndex() == 0
        ? basicFunction_ : (tabs_->currentIndex() == 1 ? advancedFunction_ : improperFunction_);
    active->setText(favorites_->currentText());
}

void MainWindow::insertTemplate() {
    QLineEdit* active = tabs_->currentIndex() == 0
        ? basicFunction_ : (tabs_->currentIndex() == 1 ? advancedFunction_ : improperFunction_);
    active->setText(templates_->currentData().toString());
}

void MainWindow::refillFromHistory(QListWidgetItem* item) {
    const QVariantMap record = item->data(Qt::UserRole).toMap();
    if (record.isEmpty()) return;
    const int tab = record.value("tab").toInt();
    tabs_->setCurrentIndex(tab);
    if (tab == 0) {
        basicFunction_->setText(record.value("function").toString());
        basicParameters_->setText(record.value("parameters").toString());
        basicLower_->setText(record.value("lower").toString());
        basicUpper_->setText(record.value("upper").toString());
    } else if (tab == 1) {
        advancedFunction_->setText(record.value("function").toString());
        advancedParameters_->setText(record.value("parameters").toString());
        advancedLower_->setText(record.value("lower").toString());
        advancedUpper_->setText(record.value("upper").toString());
        advancedSplit_->setText(record.value("split").toString());
        advancedDelta_->setText(record.value("delta").toString());
        advancedMode_->setCurrentText(record.value("mode").toString());
        advancedMethod_->setCurrentText(record.value("method").toString());
    } else {
        improperFunction_->setText(record.value("function").toString());
        improperParameters_->setText(record.value("parameters").toString());
        improperLower_->setText(record.value("lower").toString());
        improperUpper_->setText(record.value("upper").toString());
    }
}

void MainWindow::updateAdvancedRecommendation() {
    const QString expression = advancedFunction_->text().trimmed().toLower();
    const QString limits = (advancedLower_->text() + advancedUpper_->text()).toLower();
    if (limits.contains("inf") || limits.contains("oo")) {
        recommendedMethod_ = "Adaptive Simpson";
        advancedRecommendation_->setText(
            tr("Recommendation: use Adaptive Simpson or the Improper Integral tab for infinite limits.")
        );
    } else if (expression.contains("piecewise") || expression.contains("abs(") ||
               expression.contains("sin(x^") || expression.contains("cos(x^")) {
        recommendedMethod_ = "Adaptive Simpson";
        advancedRecommendation_->setText(
            tr("Recommendation: Adaptive Simpson handles rapid changes and nonsmooth behavior well.")
        );
    } else if (QRegularExpression("^[0-9x+\\-*/^(). ]+$").match(expression).hasMatch()) {
        recommendedMethod_ = "Simpson";
        advancedRecommendation_->setText(
            tr("Recommendation: Simpson is efficient for smooth polynomial-like functions.")
        );
    } else {
        recommendedMethod_ = "Gaussian Quadrature";
        advancedRecommendation_->setText(
            tr("Recommendation: Gaussian Quadrature is a strong default for smooth finite intervals.")
        );
    }
}

void MainWindow::applyAdvancedRecommendation() {
    advancedMode_->setCurrentText("Numerical Integration");
    advancedMethod_->setCurrentText(recommendedMethod_);
}

void MainWindow::showMathTools() {
    auto activeFunction = [this]() -> QLineEdit* {
        if (tabs_->currentIndex() == 0) return basicFunction_;
        if (tabs_->currentIndex() == 1) return advancedFunction_;
        return improperFunction_;
    };
    auto activeParameters = [this]() -> QLineEdit* {
        if (tabs_->currentIndex() == 0) return basicParameters_;
        if (tabs_->currentIndex() == 1) return advancedParameters_;
        return improperParameters_;
    };
    MathToolsDialog dialog(
        [activeFunction](const QString& value) { activeFunction()->setText(value); },
        [activeParameters](const QString& value) { activeParameters()->setText(value); },
        this
    );
    dialog.exec();
}

void MainWindow::applyTheme(const QString& name) {
    const bool dark = name == "Dark";
    plot_->setDarkMode(dark);
    basicPreview_->setDarkMode(dark);
    qApp->setStyleSheet(dark
        ? "QWidget{background:#202124;color:#e8eaed;} QLineEdit,QComboBox,QListWidget{background:#303134;border:1px solid #5f6368;padding:5px;} QPushButton{background:#3c4043;border:1px solid #5f6368;padding:7px 12px;} QPushButton:hover{background:#4a4d51;}"
        : "QWidget{background:#f8f9fa;color:#202124;} QLineEdit,QComboBox,QListWidget{background:white;border:1px solid #c7cbd1;padding:5px;} QPushButton{background:#ffffff;border:1px solid #b8bdc5;padding:7px 12px;} QPushButton:hover{background:#eef2f7;}"
    );
}

void MainWindow::applyLanguage(const QString& name) {
    const QMap<QString, QStringList> translations = {
        {"English", {"Integral Calculator C++", "Basic Integration", "Advanced Integration", "Improper Integral"}},
        {QStringLiteral("简体中文"), {QStringLiteral("积分计算器 C++"), QStringLiteral("基础积分"), QStringLiteral("高级积分"), QStringLiteral("反常积分")}},
        {QStringLiteral("繁體中文"), {QStringLiteral("積分計算器 C++"), QStringLiteral("基礎積分"), QStringLiteral("進階積分"), QStringLiteral("瑕積分")}},
        {"Español", {"Calculadora de integrales C++", "Integración básica", "Integración avanzada", "Integral impropia"}},
        {"Français", {"Calculateur d'intégrales C++", "Intégration de base", "Intégration avancée", "Intégrale impropre"}},
        {QStringLiteral("日本語"), {QStringLiteral("積分計算機 C++"), QStringLiteral("基本積分"), QStringLiteral("高度な積分"), QStringLiteral("広義積分")}},
        {QStringLiteral("한국어"), {QStringLiteral("적분 계산기 C++"), QStringLiteral("기본 적분"), QStringLiteral("고급 적분"), QStringLiteral("이상 적분")}},
        {QStringLiteral("العربية"), {QStringLiteral("حاسبة التكامل C++"), QStringLiteral("التكامل الأساسي"), QStringLiteral("التكامل المتقدم"), QStringLiteral("التكامل غير الصحيح")}},
        {QStringLiteral("हिन्दी"), {QStringLiteral("समाकलन कैलकुलेटर C++"), QStringLiteral("मूल समाकलन"), QStringLiteral("उन्नत समाकलन"), QStringLiteral("अनुचित समाकलन")}}
    };
    const QStringList text = translations.value(name, translations.value("English"));
    setWindowTitle(text[0]);
    tabs_->setTabText(0, text[1]);
    tabs_->setTabText(1, text[2]);
    tabs_->setTabText(2, text[3]);
    setLayoutDirection(name == QStringLiteral("العربية") ? Qt::RightToLeft : Qt::LeftToRight);
}

}  // namespace calculator
