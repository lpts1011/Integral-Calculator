#include "calculator/PlotWidget.hpp"

#include <QPainter>
#include <QPainterPath>
#include <algorithm>
#include <cmath>
#include <limits>

namespace calculator {

PlotWidget::PlotWidget(QWidget* parent) : QWidget(parent) {
    setMinimumSize(420, 300);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
}

void PlotWidget::setSeries(QVector<QPointF> points) {
    points_ = std::move(points);
    update();
}

void PlotWidget::clearSeries() {
    points_.clear();
    update();
}

void PlotWidget::setDarkMode(bool enabled) {
    darkMode_ = enabled;
    update();
}

void PlotWidget::paintEvent(QPaintEvent*) {
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);
    const QColor background = darkMode_ ? QColor("#202124") : QColor("#ffffff");
    const QColor foreground = darkMode_ ? QColor("#e8eaed") : QColor("#202124");
    const QColor grid = darkMode_ ? QColor("#3c4043") : QColor("#e0e3e7");
    painter.fillRect(rect(), background);

    const QRectF area = rect().adjusted(42, 18, -18, -34);
    painter.setPen(QPen(grid, 1));
    for (int index = 0; index <= 10; ++index) {
        const double x = area.left() + area.width() * index / 10.0;
        const double y = area.top() + area.height() * index / 10.0;
        painter.drawLine(QPointF(x, area.top()), QPointF(x, area.bottom()));
        painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y));
    }
    painter.setPen(QPen(foreground, 1.2));
    painter.drawRect(area);

    if (points_.size() < 2) {
        painter.drawText(area, Qt::AlignCenter, tr("Function plot"));
        return;
    }

    double minX = points_.front().x();
    double maxX = points_.back().x();
    double minY = std::numeric_limits<double>::infinity();
    double maxY = -std::numeric_limits<double>::infinity();
    for (const auto& point : points_) {
        if (std::isfinite(point.y())) {
            minY = std::min(minY, point.y());
            maxY = std::max(maxY, point.y());
        }
    }
    if (!std::isfinite(minY) || !std::isfinite(maxY)) {
        return;
    }
    if (std::abs(maxY - minY) < 1e-12) {
        minY -= 1.0;
        maxY += 1.0;
    }
    const double padding = (maxY - minY) * 0.08;
    minY -= padding;
    maxY += padding;

    QPainterPath path;
    bool active = false;
    for (const auto& point : points_) {
        if (!std::isfinite(point.y())) {
            active = false;
            continue;
        }
        const double px = area.left() + (point.x() - minX) * area.width() / (maxX - minX);
        const double py = area.bottom() - (point.y() - minY) * area.height() / (maxY - minY);
        if (!active) {
            path.moveTo(px, py);
            active = true;
        } else {
            path.lineTo(px, py);
        }
    }
    painter.setPen(QPen(QColor("#1a73e8"), 2.2));
    painter.drawPath(path);
    painter.setPen(foreground);
    painter.drawText(QRectF(area.left(), area.bottom() + 6, area.width(), 22), Qt::AlignCenter,
                     QStringLiteral("x: %1 to %2").arg(minX, 0, 'g', 5).arg(maxX, 0, 'g', 5));
}

}  // namespace calculator

