#!/usr/bin/env bash
# ============================================================================
# build_solvers.sh  --  Build mGear Maya solver plugins (.bundle / .so)
#
# Usage:
#   ./build_solvers.sh              (auto-detect Maya 2024-2027)
#   ./build_solvers.sh 2027         (target a specific Maya version)
#   ./build_solvers.sh clean        (delete build folder and rebuild)
#   ./build_solvers.sh clean 2027   (clean + specific version)
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
CMAKE_DIR="$SCRIPT_DIR/cmake"

# ----- Parse arguments -------------------------------------------------------
MAYA_VER=""
DO_CLEAN=0

if [[ "$1" == "clean" ]]; then
    DO_CLEAN=1
    [[ -n "$2" ]] && MAYA_VER="$2"
elif [[ -n "$1" ]]; then
    MAYA_VER="$1"
fi

# ----- Detect platform -------------------------------------------------------
OS="$(uname -s)"
case "$OS" in
    Darwin)
        PLATFORM="osx"
        PLUGIN_EXT=".bundle"
        ;;
    Linux)
        PLATFORM="linux"
        PLUGIN_EXT=".so"
        ;;
    *)
        echo "ERROR: Unsupported platform: $OS"
        exit 1
        ;;
esac

# ----- Auto-detect Maya version ----------------------------------------------
if [[ -z "$MAYA_VER" ]]; then
    for VER in 2027 2026 2025 2024 2023; do
        if [[ "$PLATFORM" == "osx" ]]; then
            MAYA_PATH="/Applications/Autodesk/maya${VER}/Maya.app/Contents"
        else
            MAYA_PATH="/usr/autodesk/maya${VER}"
        fi
        if [[ -d "$MAYA_PATH/include/maya" ]]; then
            MAYA_VER="$VER"
            break
        fi
    done
    if [[ -z "$MAYA_VER" ]]; then
        echo ""
        echo "  ERROR: Could not find a Maya SDK installation."
        echo "         Pass the version as argument:  ./build_solvers.sh 2027"
        echo ""
        exit 1
    fi
fi

# ----- Set paths --------------------------------------------------------------
if [[ "$PLATFORM" == "osx" ]]; then
    MAYA_ROOT="/Applications/Autodesk/maya${MAYA_VER}/Maya.app/Contents"
else
    MAYA_ROOT="/usr/autodesk/maya${MAYA_VER}"
fi

BUILD_DIR="$CMAKE_DIR/build_${MAYA_VER}"
PLUGIN_DIR="$SCRIPT_DIR/release/platforms/${MAYA_VER}/${PLATFORM}/x64/plug-ins"

echo ""
echo "  mGear Solver Plugin Build"
echo "  ========================="
echo "  Platform     : $PLATFORM"
echo "  Maya version : $MAYA_VER"
echo "  Maya root    : $MAYA_ROOT"
echo "  Build dir    : $BUILD_DIR"
echo "  Output dir   : $PLUGIN_DIR"
echo ""

# ----- Clean if requested ----------------------------------------------------
if [[ "$DO_CLEAN" -eq 1 ]]; then
    echo "  Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    echo ""
fi

# ----- Create directories ----------------------------------------------------
mkdir -p "$BUILD_DIR"
mkdir -p "$PLUGIN_DIR"

# ----- Configure with CMake --------------------------------------------------
echo "  [1/3] Configuring with CMake..."
echo ""

if [[ "$PLATFORM" == "osx" ]]; then
    cmake -G "Xcode" \
        -DMAYA_VERSION="$MAYA_VER" \
        -DCMAKE_OSX_ARCHITECTURES="x86_64;arm64" \
        -S "$SCRIPT_DIR" -B "$BUILD_DIR"
else
    cmake -G "Unix Makefiles" \
        -DMAYA_VERSION="$MAYA_VER" \
        -S "$SCRIPT_DIR" -B "$BUILD_DIR"
fi

# ----- Build ------------------------------------------------------------------
echo ""
echo "  [2/3] Building (Release)..."
echo ""
cmake --build "$BUILD_DIR" --config Release

# ----- Copy output ------------------------------------------------------------
echo ""
echo "  [3/3] Copying plugins to $PLUGIN_DIR..."
echo ""

FOUND=0
for f in "$BUILD_DIR"/src/Release/*"$PLUGIN_EXT" "$BUILD_DIR"/Release/*"$PLUGIN_EXT" "$BUILD_DIR"/*"$PLUGIN_EXT"; do
    if [[ -f "$f" ]]; then
        cp "$f" "$PLUGIN_DIR/"
        echo "    Copied: $(basename "$f")"
        FOUND=$((FOUND + 1))
    fi
done

if [[ "$FOUND" -eq 0 ]]; then
    echo "  WARNING: No $PLUGIN_EXT files found in build output."
    echo "  Check $BUILD_DIR for the compiled plugins."
    exit 1
fi

# ----- Verify macOS universal binary ------------------------------------------
if [[ "$PLATFORM" == "osx" ]]; then
    echo ""
    echo "  Verifying architecture..."
    for f in "$PLUGIN_DIR"/*"$PLUGIN_EXT"; do
        lipo -info "$f"
    done
fi

echo ""
echo "  ========================================="
echo "  BUILD SUCCESSFUL"
echo "  Plugins in: $PLUGIN_DIR"
echo "  ========================================="
echo ""
