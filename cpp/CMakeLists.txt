cmake_minimum_required(VERSION 3.24)

project(IntegralCalculatorCpp VERSION 4.0.0 LANGUAGES CXX)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(ENABLE_SAMPLES OFF CACHE BOOL "" FORCE)
set(ENABLE_OPENMP OFF CACHE BOOL "" FORCE)
set(ENABLE_WIDE_CHAR OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
add_subdirectory(third_party/muparser EXCLUDE_FROM_ALL)
set(BUILD_TESTING ON CACHE BOOL "" FORCE)

find_package(Qt6 6.5 REQUIRED COMPONENTS Widgets Concurrent)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

add_library(calculator_core STATIC
    src/ExpressionEngine.cpp
    src/MathExtensions.cpp
    src/NumericalIntegrator.cpp
    src/SymbolicEngine.cpp
)
target_include_directories(calculator_core PUBLIC include)
target_link_libraries(calculator_core PUBLIC muparser::muparser)

add_executable(IntegralCalculator MACOSX_BUNDLE
    src/main.cpp
    src/IntegralPreviewWidget.cpp
    src/MainWindow.cpp
    src/MathToolsDialog.cpp
    src/PlotWidget.cpp
    include/calculator/MainWindow.hpp
    include/calculator/IntegralPreviewWidget.hpp
    include/calculator/PlotWidget.hpp
    include/calculator/MathToolsDialog.hpp
)
target_link_libraries(IntegralCalculator PRIVATE
    calculator_core
    Qt6::Widgets
    Qt6::Concurrent
)
set_target_properties(IntegralCalculator PROPERTIES
    MACOSX_BUNDLE_BUNDLE_NAME "Integral Calculator C++"
    MACOSX_BUNDLE_GUI_IDENTIFIER "com.peichili.integralcalculator.cpp"
    MACOSX_BUNDLE_SHORT_VERSION_STRING "4.0.0"
    OUTPUT_NAME "Integral Calculator C++"
)

enable_testing()
add_executable(calculator_tests tests/test_core.cpp)
target_link_libraries(calculator_tests PRIVATE calculator_core)
add_test(NAME calculator_core_tests COMMAND calculator_tests)

add_executable(calculator_preview_tests
    tests/test_preview.cpp
    src/IntegralPreviewWidget.cpp
    include/calculator/IntegralPreviewWidget.hpp
)
target_link_libraries(calculator_preview_tests PRIVATE calculator_core Qt6::Widgets)
add_test(NAME calculator_preview_updates COMMAND calculator_preview_tests)
