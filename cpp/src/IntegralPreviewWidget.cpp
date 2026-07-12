#include "calculator/IntegralPreviewWidget.hpp"

#include "calculator/ExpressionEngine.hpp"

#include <QPainter>
#include <QRegularExpression>
#include <QTextDocument>

#include <algorithm>

namespace calculator {
namespace {

QString displayConstant(QString text) {
    text = text.trimmed();
    text.replace(QRegularExpression(QStringLiteral("\\bpi\\b")), QStringLiteral("π"));
    text.replace(QRegularExpression(QStringLiteral("^[+]?(?:inf|oo)$")), QStringLiteral("∞"));
    text.replace(QRegularExpression(QStringLiteral("^-(?:inf|oo)$")), QStringLiteral("−∞"));
    return text;
}

QString expressionHtml(QString expression) {
    expression.replace(QStringLiteral("**"), QStringLiteral("^"));
    expression.replace(QRegularExpression(QStringLiteral("\\bpi\\b")), QStringLiteral("π"));
    expression.replace(QRegularExpression(QStringLiteral("\\bsqrt\\s*\\(")), QStringLiteral("√("));
    expression = expression.toHtmlEscaped();
    expression.replace(QStringLiteral("*"), QStringLiteral(" · "));

    const QRegularExpression exponent(
        QStringLiteral(R"(\^\s*(\([^()]*(?:\([^()]*\)[^()]*)*\)|[+-]?(?:[A-Za-z0-9_.]+)))")
    );
    int offset = 0;
    while (true) {
        const auto match = exponent.match(expression, offset);
        if (!match.hasMatch()) {
            break;
        }
        QString value = match.captured(1);
        if (value.startsWith('(') && value.endsWith(')')) {
            value = value.mid(1, value.size() - 2);
        }
        const QString replacement = QStringLiteral("<sup>%1</sup>").arg(value);
        expression.replace(match.capturedStart(), match.capturedLength(), replacement);
        offset = match.capturedStart() + replacement.size();
    }
    return expression;
}

}  // namespace

IntegralPreviewWidget::IntegralPreviewWidget(QWidget* parent) : QWidget(parent) {
    setMinimumHeight(118);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
}

void IntegralPreviewWidget::setInput(
    const QString& expression,
    const QString& parameters,
    const QString& lower,
    const QString& upper
) {
    const QString trimmedExpression = expression.trimmed();
    hasExpression_ = !trimmedExpression.isEmpty();
    hasBounds_ = false;
    invalid_ = false;
    expressionHtml_.clear();
    lowerText_.clear();
    upperText_.clear();

    if (!hasExpression_) {
        update();
        return;
    }

    try {
        const auto parameterMap = ExpressionEngine::parseParameters(parameters.trimmed().toStdString());
        ExpressionEngine validator(trimmedExpression.toStdString(), parameterMap);
        validator.evaluate(0.6180339887498948);

        const auto substituted = ExpressionEngine::substituteParameters(
            trimmedExpression.toStdString(), parameterMap
        );
        expressionHtml_ = expressionHtml(QString::fromStdString(substituted));

        if (!lower.trimmed().isEmpty() && !upper.trimmed().isEmpty()) {
            const auto parseBound = [](const QString& value) {
                const QString normalized = value.trimmed().toLower();
                if (normalized == "inf" || normalized == "+inf" ||
                    normalized == "oo" || normalized == "+oo" ||
                    normalized == "-inf" || normalized == "-oo") {
                    return;
                }
                ExpressionEngine::parseConstant(normalized.toStdString());
            };
            parseBound(lower);
            parseBound(upper);
            lowerText_ = displayConstant(lower);
            upperText_ = displayConstant(upper);
            hasBounds_ = true;
        }
    } catch (...) {
        invalid_ = true;
    }
    update();
}

void IntegralPreviewWidget::setDarkMode(bool enabled) {
    darkMode_ = enabled;
    update();
}

void IntegralPreviewWidget::paintEvent(QPaintEvent*) {
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);
    const QColor foreground = darkMode_ ? QColor("#e8eaed") : QColor("#202124");
    painter.setPen(foreground);

    if (!hasExpression_) {
        return;
    }
    if (invalid_) {
        QFont font = painter.font();
        font.setPointSize(16);
        painter.setFont(font);
        painter.drawText(rect(), Qt::AlignCenter, tr("(invalid input)"));
        return;
    }

    QTextDocument document;
    QFont expressionFont = font();
    expressionFont.setPointSize(20);
    document.setDefaultFont(expressionFont);
    document.setDefaultStyleSheet(QStringLiteral("body { color: %1; }").arg(foreground.name()));
    document.setHtml(QStringLiteral("<body>%1</body>").arg(expressionHtml_));
    document.setTextWidth(std::min(560.0, width() * 0.62));

    const qreal documentWidth = document.idealWidth();
    const qreal documentHeight = document.size().height();
    const qreal integralWidth = hasBounds_ ? 86.0 : 0.0;
    const qreal dxWidth = hasBounds_ ? 42.0 : 0.0;
    const qreal totalWidth = integralWidth + documentWidth + dxWidth;
    const qreal startX = std::max(8.0, (width() - totalWidth) / 2.0);
    const qreal centerY = height() / 2.0;

    if (hasBounds_) {
        QFont integralFont = painter.font();
        integralFont.setPointSize(56);
        painter.setFont(integralFont);
        painter.drawText(QRectF(startX, 8, 50, height() - 16), Qt::AlignCenter, QStringLiteral("∫"));

        QFont boundsFont = painter.font();
        boundsFont.setPointSize(13);
        painter.setFont(boundsFont);
        painter.drawText(QRectF(startX + 42, 5, 58, 26), Qt::AlignLeft | Qt::AlignVCenter, upperText_);
        painter.drawText(
            QRectF(startX + 42, height() - 31, 58, 26),
            Qt::AlignLeft | Qt::AlignVCenter,
            lowerText_
        );
    }

    painter.save();
    painter.translate(startX + integralWidth, centerY - documentHeight / 2.0);
    document.drawContents(&painter);
    painter.restore();

    if (hasBounds_) {
        QFont dxFont = painter.font();
        dxFont.setPointSize(20);
        painter.setFont(dxFont);
        painter.drawText(
            QRectF(startX + integralWidth + documentWidth + 6, 0, dxWidth, height()),
            Qt::AlignCenter,
            QStringLiteral("dx")
        );
    }
}

}  // namespace calculator
