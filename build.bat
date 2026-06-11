@echo off
setlocal enabledelayedexpansion
title StrangeCat Monitor - Builder

echo.
echo  ========================================
echo   STRANGECAT MONITOR  v1.1  -  Builder
echo  ========================================
echo.

:: Source directory (may contain spaces)
set "SRC=%~dp0"

:: Safe build directory WITHOUT spaces in path
set "BUILD_DIR=%TEMP%\StrangeCatBuild"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    pause & exit /b 1
)

:: Install deps
echo [1/4] Installing dependencies...
pip install pyinstaller psutil pillow pystray wmi pywin32 --quiet --upgrade
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause & exit /b 1
)

:: Copy files to temp dir without spaces
echo [2/4] Copying to safe temp folder: %BUILD_DIR%
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"
copy /y "%SRC%strangecat_monitor.py" "%BUILD_DIR%\strangecat_monitor.py" >nul
copy /y "%SRC%make_icon_stable.py"          "%BUILD_DIR%\make_icon_stable.py"          >nul

:: Generate icon in safe dir
echo [3/4] Generating icon.ico...
python "%BUILD_DIR%\make_icon_stable.py"
if not exist "%BUILD_DIR%\icon.ico" (
    echo [ERROR] icon.ico not generated.
    pause & exit /b 1
)

:: Build EXE from safe dir — no spaces anywhere in the paths passed to pyinstaller
echo [4/4] Building EXE...
cd /d "%BUILD_DIR%"

pyinstaller --onefile --windowed --name StrangeCatMonitor --icon icon.ico --distpath dist --workpath build_tmp --specpath . strangecat_monitor.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See output above.
    cd /d "%SRC%"
    pause & exit /b 1
)

:: Copy final EXE back, rename with spaces for display
if not exist "%SRC%dist" mkdir "%SRC%dist"
copy /y "%BUILD_DIR%\dist\StrangeCatMonitor.exe" "%SRC%dist\StrangeCat Monitor.exe" >nul

cd /d "%SRC%"

echo.
echo  ========================================
echo   SUCCESS!
echo   EXE: %SRC%dist\StrangeCat Monitor.exe
echo  ========================================
echo.
pause
