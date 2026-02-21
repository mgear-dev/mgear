@echo off
setlocal

:: ============================================================================
:: build_accel.bat  --  Build the C++ acceleration module for mGear RGP
::
:: Usage:
::   build_accel.bat              (auto-detect Maya 2024/2025/2026)
::   build_accel.bat 2026         (target a specific Maya version)
::   build_accel.bat clean        (delete build folder and rebuild)
::   build_accel.bat clean 2026   (clean + specific version)
:: ============================================================================

set "SCRIPT_DIR=%~dp0"
set "CPP_DIR=%SCRIPT_DIR%python_src"
set "BUILD_DIR=%CPP_DIR%\build"

:: ----- Parse arguments -----------------------------------------------------
set "MAYA_VER="
set "DO_CLEAN=0"

if /i "%~1"=="clean" (
    set "DO_CLEAN=1"
    if not "%~2"=="" set "MAYA_VER=%~2"
) else if not "%~1"=="" (
    set "MAYA_VER=%~1"
)

:: ----- Auto-detect Maya version if not specified ---------------------------
if "%MAYA_VER%"=="" (
    for %%V in (2026 2025 2024) do (
        if exist "C:\Program Files\Autodesk\Maya%%V\bin\mayapy.exe" (
            set "MAYA_VER=%%V"
            goto :found_maya
        )
    )
    echo.
    echo  ERROR: Could not find a Maya installation.
    echo         Pass the version as argument:  build_accel.bat 2026
    echo.
    exit /b 1
)
:found_maya

set "MAYA_ROOT=C:\Program Files\Autodesk\Maya%MAYA_VER%"

echo.
echo  mGear RGP C++ Accelerator Build
echo  ================================
echo  Maya version : %MAYA_VER%
echo  Maya root    : %MAYA_ROOT%
echo  Build dir    : %BUILD_DIR%
echo.

:: Verify Maya path exists
if not exist "%MAYA_ROOT%\bin\mayapy.exe" (
    echo  ERROR: Maya %MAYA_VER% not found at "%MAYA_ROOT%"
    exit /b 1
)

:: ----- Clean if requested --------------------------------------------------
if %DO_CLEAN%==1 (
    echo  Cleaning build directory...
    if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
    echo.
)

:: ----- Create build directory ----------------------------------------------
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

:: ----- Configure with CMake ------------------------------------------------
echo  [1/2] Configuring with CMake...
echo.
cmake -S "%CPP_DIR%" -B "%BUILD_DIR%" -DMAYA_ROOT="%MAYA_ROOT%"
if errorlevel 1 (
    echo.
    echo  ERROR: CMake configure failed.
    echo         Make sure CMake is installed and on your PATH.
    echo         You may also need Visual Studio Build Tools installed.
    exit /b 1
)

:: ----- Build ---------------------------------------------------------------
echo.
echo  [2/2] Building (Release)...
echo.
cmake --build "%BUILD_DIR%" --config Release
if errorlevel 1 (
    echo.
    echo  ERROR: Build failed. Check the errors above.
    exit /b 1
)

:: ----- Verify output -------------------------------------------------------
echo.

set "FOUND_PYD="
for %%F in ("%SCRIPT_DIR%release\scripts\mgear\shifter\_rgp_accel_cpp*.pyd") do set "FOUND_PYD=%%F"

if defined FOUND_PYD (
    echo  =========================================
    echo  BUILD SUCCESSFUL
    echo  Output: %FOUND_PYD%
    echo  =========================================
    echo.
    echo  Reload Maya %MAYA_VER% with mGear to use C++ acceleration.
) else (
    echo  WARNING: Build completed but .pyd not found at expected location.
    echo  Check %BUILD_DIR% for the output file.
)

echo.
pause
endlocal
