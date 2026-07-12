#pragma once

#include <QString>
#include <QWidget>

namespace calculator {

class IntegralPreviewWidget final : public QWidget {
public:
    explicit IntegralPreviewWidget(QWidget* parent = nullptr);

    void setInput(
        const QString& expression,
        const QString& parameters,
        const QString& lower,
        const QString& upper
    );
    void setDarkMode(bool enabled);

protected:
    void paintEvent(QPaintEvent* event) override;

private:
    QString expressionHtml_;
    QString lowerText_;
    QString upperText_;
    bool hasExpression_ = false;
    bool hasBounds_ = false;
    bool invalid_ = false;
    bool darkMode_ = false;
};

}  // namespace calculator
