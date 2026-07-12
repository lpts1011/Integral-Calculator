#pragma once

#include <QPointF>
#include <QVector>
#include <QWidget>

namespace calculator {

class PlotWidget final : public QWidget {
    Q_OBJECT

public:
    explicit PlotWidget(QWidget* parent = nullptr);

    void setSeries(QVector<QPointF> points);
    void clearSeries();
    void setDarkMode(bool enabled);

protected:
    void paintEvent(QPaintEvent* event) override;

private:
    QVector<QPointF> points_;
    bool darkMode_ = false;
};

}  // namespace calculator

