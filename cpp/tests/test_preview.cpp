#include "calculator/IntegralPreviewWidget.hpp"

#include <QApplication>
#include <QImage>
#include <QPainter>

#include <iostream>
#include <stdexcept>

namespace {

QImage renderPreview(calculator::IntegralPreviewWidget& preview) {
    QImage image(preview.size(), QImage::Format_ARGB32_Premultiplied);
    image.fill(Qt::white);
    QPainter painter(&image);
    preview.render(&painter);
    return image;
}

void requireDifferent(const QImage& first, const QImage& second, const char* name) {
    if (first == second) {
        throw std::runtime_error(std::string(name) + " did not update the preview image");
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    QApplication application(argc, argv);
    calculator::IntegralPreviewWidget preview;
    preview.resize(760, 130);

    preview.setInput("x^2", "", "0", "1");
    const QImage polynomial = renderPreview(preview);

    preview.setInput("sin(x)", "", "0", "pi");
    const QImage trigonometric = renderPreview(preview);
    requireDifferent(polynomial, trigonometric, "expression change");

    preview.setInput("a*x^2", "a=3", "-1", "1");
    const QImage parameterized = renderPreview(preview);
    requireDifferent(trigonometric, parameterized, "parameter change");

    preview.setInput("sin(", "", "0", "1");
    const QImage invalid = renderPreview(preview);
    requireDifferent(parameterized, invalid, "invalid input");

    std::cout << "Integral preview updates passed.\n";
    return 0;
}
