#include "calculator/MainWindow.hpp"

#include <QApplication>
#include <QStyleFactory>
#include <QTimer>

int main(int argc, char* argv[]) {
    QApplication application(argc, argv);
    application.setApplicationName(QStringLiteral("Integral Calculator C++"));
    application.setOrganizationName(QStringLiteral("Peichi Li"));
    application.setStyle(QStyleFactory::create(QStringLiteral("Fusion")));

    calculator::MainWindow window;
    window.show();

    const QStringList arguments = application.arguments();
    const int screenshotIndex = arguments.indexOf(QStringLiteral("--screenshot"));
    if (screenshotIndex >= 0 && screenshotIndex + 1 < arguments.size()) {
        const QString outputPath = arguments.at(screenshotIndex + 1);
        QTimer::singleShot(500, &application, [&application, &window, outputPath] {
            window.grab().save(outputPath);
            application.quit();
        });
    }
    return application.exec();
}
