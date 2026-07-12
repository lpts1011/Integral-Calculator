#pragma once

#include <QDialog>

#include <functional>

class QString;
class QTabWidget;

namespace calculator {

class MathToolsDialog final : public QDialog {
public:
    using InsertHandler = std::function<void(const QString&)>;

    explicit MathToolsDialog(
        InsertHandler insertFunction,
        InsertHandler insertParameter,
        QWidget* parent = nullptr
    );

private:
    QTabWidget* tabs_ = nullptr;
    InsertHandler insertFunction_;
    InsertHandler insertParameter_;

    void buildTools();
};

}  // namespace calculator
