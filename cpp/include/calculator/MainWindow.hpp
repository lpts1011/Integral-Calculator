#pragma once

#include <QMainWindow>
#include <QPointF>
#include <QVector>
#include <QVariantMap>
#include <functional>

class QComboBox;
class QLabel;
class QLineEdit;
class QListWidget;
class QListWidgetItem;
class QProgressBar;
class QPushButton;
class QTabWidget;

namespace calculator {

class PlotWidget;
class IntegralPreviewWidget;

struct CalculationOutput {
    bool success = false;
    QString resultText;
    QString historyText;
    QString errorText;
    QString exactText;
    QVector<QPointF> plotPoints;
    QVariantMap record;
};

class MainWindow final : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);

private slots:
    void calculateBasic();
    void calculateAdvanced();
    void calculateImproper();
    void compareMethods();
    void resetAll();
    void exportHistory();
    void showSteps();
    void showSuggestions();
    void showMathTools();
    void showBasicExactResult();
    void updateBasicPreview();
    void showUsage();
    void addFavorite();
    void insertFavorite();
    void insertTemplate();
    void refillFromHistory(QListWidgetItem* item);
    void updateAdvancedRecommendation();
    void applyAdvancedRecommendation();
    void applyTheme(const QString& name);
    void applyLanguage(const QString& name);

private:
    void buildInterface();
    QWidget* buildBasicTab();
    QWidget* buildAdvancedTab();
    QWidget* buildImproperTab();
    void runTask(std::function<CalculationOutput()> task, QLabel* targetLabel);
    void finishTask(const CalculationOutput& output, QLabel* targetLabel);
    static double parseLimit(const QString& text);
    static QVector<QPointF> sampleFunction(
        const std::string& expression,
        const std::string& parameters,
        double lower,
        double upper
    );

    QTabWidget* tabs_ = nullptr;
    PlotWidget* plot_ = nullptr;
    QListWidget* history_ = nullptr;
    QProgressBar* progress_ = nullptr;
    QComboBox* language_ = nullptr;
    QComboBox* theme_ = nullptr;
    QComboBox* favorites_ = nullptr;
    QComboBox* templates_ = nullptr;

    QLineEdit* basicFunction_ = nullptr;
    QLineEdit* basicParameters_ = nullptr;
    QLineEdit* basicLower_ = nullptr;
    QLineEdit* basicUpper_ = nullptr;
    IntegralPreviewWidget* basicPreview_ = nullptr;
    QLabel* basicResult_ = nullptr;
    QPushButton* basicCalculate_ = nullptr;
    QPushButton* basicExact_ = nullptr;

    QLineEdit* advancedFunction_ = nullptr;
    QLineEdit* advancedParameters_ = nullptr;
    QLineEdit* advancedLower_ = nullptr;
    QLineEdit* advancedUpper_ = nullptr;
    QLineEdit* advancedSplit_ = nullptr;
    QLineEdit* advancedDelta_ = nullptr;
    QComboBox* advancedMode_ = nullptr;
    QComboBox* advancedMethod_ = nullptr;
    QLabel* advancedResult_ = nullptr;
    QPushButton* advancedCalculate_ = nullptr;
    QPushButton* compare_ = nullptr;
    QLabel* advancedRecommendation_ = nullptr;
    QPushButton* applyRecommendation_ = nullptr;
    QString recommendedMethod_;

    QLineEdit* improperFunction_ = nullptr;
    QLineEdit* improperParameters_ = nullptr;
    QLineEdit* improperLower_ = nullptr;
    QLineEdit* improperUpper_ = nullptr;
    QLabel* improperResult_ = nullptr;
    QPushButton* improperCalculate_ = nullptr;

    QString lastSteps_;
    QString lastBasicExactText_;
    int activeTasks_ = 0;
};

}  // namespace calculator
