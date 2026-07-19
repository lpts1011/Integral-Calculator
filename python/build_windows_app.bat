@echo off
setlocal

cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON=py
) else (
    set PYTHON=python
)

%PYTHON% --version >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python from https://www.python.org/downloads/windows/
    exit /b 1
)

%PYTHON% -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo Installing Windows build dependencies...
    %PYTHON% -m pip install -r requirements-windows.txt
    if errorlevel 1 exit /b 1
)

%PYTHON% -m PyInstaller --clean --noconfirm windows_app.spec
if errorlevel 1 exit /b 1

echo.
echo Built: dist\Integral_Calculator_Python\Integral_Calculator_Python.exe
