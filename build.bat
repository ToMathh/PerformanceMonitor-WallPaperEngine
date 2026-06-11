@echo off
setlocal enabledelayedexpansion
title StrangeCat Server (UltraLowPerf) - Builder

echo.
echo  ============================================
echo   STRANGECAT SERVER  (UltraLowPerf)  Builder
echo  ============================================
echo.

:: This script's folder (UltraLowPerf\)
set "HERE=%~dp0"
:: Project root (parent of UltraLowPerf)
set "SRC=%~dp0.."

:: Safe build directory WITHOUT spaces in path
set "BUILD_DIR=%TEMP%\StrangeCatServerBuild"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    pause & exit /b 1
)

echo [1/4] Installing dependencies...
pip install pyinstaller psutil pillow pystray wmi pywin32 --quiet --upgrade 2>nul
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause & exit /b 1
)

echo [2/4] Copying to safe temp folder: %BUILD_DIR%
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"
xcopy /e /i /y /q "%SRC%\base" "%BUILD_DIR%\base" >nul
copy /y "%HERE%main.py"      "%BUILD_DIR%\main.py"      >nul
copy /y "%SRC%\make_icon.py" "%BUILD_DIR%\make_icon.py" >nul

echo [3/4] Generating icon.ico...
python "%BUILD_DIR%\make_icon.py"
if not exist "%BUILD_DIR%\icon.ico" (
    echo [ERROR] icon.ico not generated.
    pause & exit /b 1
)

echo [4/4] Building EXE...
cd /d "%BUILD_DIR%"

pyinstaller --onefile --windowed --name StrangeCatServer --icon icon.ico ^
    --distpath dist --workpath build_tmp --specpath . ^
    --paths "%BUILD_DIR%" --paths "%BUILD_DIR%\base" ^
    --hidden-import config --hidden-import collector --hidden-import metrics ^
    --hidden-import http_server --hidden-import datastore ^
    --hidden-import wmi --hidden-import win32com --hidden-import win32com.client ^
    --hidden-import pystray --hidden-import PIL.Image --hidden-import PIL.ImageDraw ^
    "%BUILD_DIR%\main.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above.
    cd /d "%HERE%"
    pause & exit /b 1
)

:: Copy final EXE back with a friendly (spaced) name
if not exist "%HERE%dist" mkdir "%HERE%dist"
copy /y "%BUILD_DIR%\dist\StrangeCatServer.exe" "%HERE%dist\StrangeCat Server.exe" >nul

cd /d "%HERE%"

echo.
echo  ============================================
echo   SUCCESS!
echo   EXE: %HERE%dist\StrangeCat Server.exe
echo  ============================================
echo.

echo Starting StrangeCat Server...
start "" "%HERE%dist\StrangeCat Server.exe"

timeout /t 2 >nul
