@echo off
setlocal

:: ============================================================================
:: build_solvers.bat  --  Build mGear Maya solver plugins (.mll)
::
:: Usage:
::   build_solvers.bat              (auto-detect Maya 2022-2027)
::   build_solvers.bat 2027         (target a specific Maya version)
::   build_solvers.bat clean        (delete build folder and rebuild)
::   build_solvers.bat clean 2027   (clean + specific version)
:: ============================================================================

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "CMAKE_DIR=%SCRIPT_DIR%\cmake"
set "SRC_DIR=%SCRIPT_DIR%\src"

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
    for %%V in (2027 2026 2025 2024 2023 2022) do (
        if exist "C:\Program Files\Autodesk\Maya%%V\include\maya\MFn.h" (
            set "MAYA_VER=%%V"
            goto :found_maya
        )
    )
    echo.
    echo  ERROR: Could not find a Maya SDK installation.
    echo         Pass the version as argument:  build_solvers.bat 2027
    echo.
    exit /b 1
)
:found_maya

:: ----- Determine Visual Studio generator -----------------------------------
:: Maya 2022-2024 were built with VS 2019; 2025+ with VS 2022.
set "VS_GEN=Visual Studio 17 2022"
if "%MAYA_VER%"=="2024" set "VS_GEN=Visual Studio 16 2019"
if "%MAYA_VER%"=="2023" set "VS_GEN=Visual Studio 16 2019"
if "%MAYA_VER%"=="2022" set "VS_GEN=Visual Studio 16 2019"

set "MAYA_ROOT=C:\Program Files\Autodesk\Maya%MAYA_VER%"
set "BUILD_DIR=%CMAKE_DIR%\build_%MAYA_VER%"
set "PLUGIN_DIR=%SCRIPT_DIR%\release\platforms\%MAYA_VER%\windows\x64\plug-ins"

echo.
echo  mGear Solver Plugin Build
echo  =========================
echo  Maya version : %MAYA_VER%
echo  Maya root    : %MAYA_ROOT%
echo  VS generator : %VS_GEN%
echo  Build dir    : %BUILD_DIR%
echo  Output dir   : %PLUGIN_DIR%
echo.

:: Verify Maya SDK exists
if not exist "%MAYA_ROOT%\include\maya\MFn.h" (
    echo  ERROR: Maya %MAYA_VER% SDK not found at "%MAYA_ROOT%\include\maya\"
    exit /b 1
)

:: ----- Clean if requested --------------------------------------------------
if %DO_CLEAN%==1 (
    echo  Cleaning build directory...
    if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
    echo.
)

:: ----- Create directories --------------------------------------------------
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
if not exist "%PLUGIN_DIR%" mkdir "%PLUGIN_DIR%"

:: ----- Configure with CMake ------------------------------------------------
echo  [1/3] Configuring with CMake...
echo.
cmake -G "%VS_GEN%" -A x64 -DMAYA_VERSION=%MAYA_VER% -S "%SCRIPT_DIR%" -B "%BUILD_DIR%"
if errorlevel 1 (
    echo.
    echo  ERROR: CMake configure failed.
    echo         Make sure CMake and Visual Studio Build Tools are installed.
    exit /b 1
)

:: ----- Build ---------------------------------------------------------------
echo.
echo  [2/3] Building (Release)...
echo.
cmake --build "%BUILD_DIR%" --config Release
if errorlevel 1 (
    echo.
    echo  ERROR: Build failed. Check the errors above.
    exit /b 1
)

:: ----- Copy output to platforms directory ----------------------------------
echo.
echo  [3/3] Copying plugins to %PLUGIN_DIR%...
echo.

set "FOUND_PLUGINS=0"

for %%D in ("%BUILD_DIR%\src\Release" "%BUILD_DIR%\Release" "%BUILD_DIR%") do (
    for %%F in ("%%~D\*.mll") do (
        copy /y "%%F" "%PLUGIN_DIR%\" >nul
        echo    Copied: %%~nxF
        set /a FOUND_PLUGINS+=1
    )
)

if %FOUND_PLUGINS%==0 (
    echo  WARNING: No .mll files found in build output.
    echo  Check %BUILD_DIR% for the compiled plugins.
    exit /b 1
)

echo.
echo  =========================================
echo  BUILD SUCCESSFUL
echo  Plugins in: %PLUGIN_DIR%
echo  =========================================
echo.

pause
endlocal
