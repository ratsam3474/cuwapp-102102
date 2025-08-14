@echo off
title WhatsApp Agent Startup

echo.
echo =====================================================
echo           WhatsApp Agent - Starting...
echo =====================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "main.py" (
    echo ERROR: main.py not found
    echo Please ensure all project files are in the current directory
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found
    echo Please ensure all project files are in the current directory
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/upgrade requirements
echo Installing/updating requirements...
pip install -r requirements.txt --quiet --disable-pip-version-check

if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

echo.
echo =====================================================
echo      WhatsApp Agent is starting...
echo      Dashboard will open at: https://app.cuwapp.com
echo      Press Ctrl+C to stop the server
echo =====================================================
echo.

REM Start the application
python start.py

echo.
echo WhatsApp Agent has stopped.
pause