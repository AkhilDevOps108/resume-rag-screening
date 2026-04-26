@echo off
REM Quick start script for the Advanced Context-Aware RAG (Windows)

echo.
echo ========================================
echo 🚀 Advanced Context-Aware RAG
echo Quick Start (Windows)
echo ========================================
echo.

REM Check Python
echo 📋 Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.9+
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    ✓ Python %PYTHON_VERSION%

REM Check Node
echo 📋 Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Node.js not found. Frontend setup will be skipped.
    echo    Install Node.js from https://nodejs.org/
) else (
    for /f %%i in ('node --version') do set NODE_VERSION=%%i
    echo    ✓ Node.js %NODE_VERSION%
)

REM Backend setup
echo.
echo 📦 Setting up Backend...
cd backend

if not exist "venv" (
    echo    Creating virtual environment...
    python -m venv venv
)

echo    Activating virtual environment...
call venv\Scripts\activate.bat

echo    Installing Python dependencies...
pip install -q -r requirements.txt

echo    ✓ Backend setup complete
cd ..

REM Frontend setup (if Node is installed)
node --version >nul 2>&1
if errorlevel 0 (
    echo.
    echo 📦 Setting up Frontend...
    cd frontend
    
    if not exist "node_modules" (
        echo    Installing Node dependencies...
        call npm install -q
    )
    
    echo    ✓ Frontend setup complete
    cd ..
)

echo.
echo ✅ Setup Complete!
echo.
echo 🎯 Next Steps:
echo    1. Open Terminal 1 - Start Backend:
echo       cd backend
echo       venv\Scripts\activate.bat
echo       python app.py
echo.
echo    2. Open Terminal 2 - Start Frontend:
echo       cd frontend
echo       npm start
echo.
echo    3. Open browser:
echo       http://localhost:3000
echo.
echo 🚀 Happy RAG-ing!
echo.
pause
