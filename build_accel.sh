#!/usr/bin/env bash
# ============================================================================
# build_accel.sh  --  Build the C++ acceleration module for mGear RGP
#
# Usage:
#   ./build_accel.sh              (auto-detect Maya 2024/2025/2026)
#   ./build_accel.sh 2026         (target a specific Maya version)
#   ./build_accel.sh clean        (delete build folder and rebuild)
#   ./build_accel.sh clean 2026   (clean + specific version)
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPP_DIR="${SCRIPT_DIR}/python_src"
BUILD_DIR="${CPP_DIR}/build"

# ----- Parse arguments -----------------------------------------------------
MAYA_VER=""
DO_CLEAN=0

if [[ "${1,,}" == "clean" ]]; then
    DO_CLEAN=1
    [[ -n "$2" ]] && MAYA_VER="$2"
elif [[ -n "$1" ]]; then
    MAYA_VER="$1"
fi

# ----- Detect platform ------------------------------------------------------
PLATFORM="$(uname -s)"
case "${PLATFORM}" in
    Linux*)
        MAYA_BASE="/usr/autodesk"
        MAYAPY_REL="bin/mayapy"
        OUTPUT_GLOB="${SCRIPT_DIR}/release/scripts/mgear/shifter/_rgp_accel_cpp*.so"
        ;;
    Darwin*)
        MAYA_BASE="/Applications/Autodesk"
        MAYAPY_REL="Maya.app/Contents/bin/mayapy"
        OUTPUT_GLOB="${SCRIPT_DIR}/release/scripts/mgear/shifter/_rgp_accel_cpp*.so"
        ;;
    *)
        echo ""
        echo "  ERROR: Unsupported platform '${PLATFORM}'."
        echo "         Use build_accel.bat on Windows."
        echo ""
        exit 1
        ;;
esac

# ----- Auto-detect Maya version if not specified ----------------------------
if [[ -z "${MAYA_VER}" ]]; then
    for VER in 2026 2025 2024; do
        if [[ "${PLATFORM}" == "Darwin"* ]]; then
            CANDIDATE="${MAYA_BASE}/maya${VER}/${MAYAPY_REL}"
        else
            CANDIDATE="${MAYA_BASE}/maya${VER}/${MAYAPY_REL}"
        fi
        if [[ -x "${CANDIDATE}" ]]; then
            MAYA_VER="${VER}"
            break
        fi
    done

    if [[ -z "${MAYA_VER}" ]]; then
        echo ""
        echo "  ERROR: Could not find a Maya installation."
        echo "         Pass the version as argument:  ./build_accel.sh 2026"
        echo ""
        exit 1
    fi
fi

# ----- Set MAYA_ROOT based on platform --------------------------------------
if [[ "${PLATFORM}" == "Darwin"* ]]; then
    MAYA_ROOT="${MAYA_BASE}/maya${MAYA_VER}/Maya.app/Contents"
    MAYAPY="${MAYA_ROOT}/bin/mayapy"
else
    MAYA_ROOT="${MAYA_BASE}/maya${MAYA_VER}"
    MAYAPY="${MAYA_ROOT}/bin/mayapy"
fi

echo ""
echo "  mGear RGP C++ Accelerator Build"
echo "  ================================"
echo "  Platform     : ${PLATFORM}"
echo "  Maya version : ${MAYA_VER}"
echo "  Maya root    : ${MAYA_ROOT}"
echo "  Build dir    : ${BUILD_DIR}"
echo ""

# Verify Maya path exists
if [[ ! -x "${MAYAPY}" ]]; then
    echo "  ERROR: Maya ${MAYA_VER} not found at '${MAYA_ROOT}'"
    echo "         mayapy not found: ${MAYAPY}"
    exit 1
fi

# ----- Clean if requested ---------------------------------------------------
if [[ ${DO_CLEAN} -eq 1 ]]; then
    echo "  Cleaning build directory..."
    rm -rf "${BUILD_DIR}"
    echo ""
fi

# ----- Create build directory -----------------------------------------------
mkdir -p "${BUILD_DIR}"

# ----- Configure with CMake -------------------------------------------------
echo "  [1/2] Configuring with CMake..."
echo ""
cmake -S "${CPP_DIR}" -B "${BUILD_DIR}" -DMAYA_ROOT="${MAYA_ROOT}" -DCMAKE_BUILD_TYPE=Release
if [[ $? -ne 0 ]]; then
    echo ""
    echo "  ERROR: CMake configure failed."
    echo "         Make sure cmake is installed and on your PATH."
    exit 1
fi

# ----- Build ----------------------------------------------------------------
echo ""
echo "  [2/2] Building (Release)..."
echo ""
cmake --build "${BUILD_DIR}" --config Release
if [[ $? -ne 0 ]]; then
    echo ""
    echo "  ERROR: Build failed. Check the errors above."
    exit 1
fi

# ----- Verify output --------------------------------------------------------
echo ""

FOUND_SO=""
for f in ${OUTPUT_GLOB}; do
    if [[ -f "$f" ]]; then
        FOUND_SO="$f"
        break
    fi
done

if [[ -n "${FOUND_SO}" ]]; then
    echo "  ========================================="
    echo "  BUILD SUCCESSFUL"
    echo "  Output: ${FOUND_SO}"
    echo "  ========================================="
    echo ""
    echo "  Reload Maya ${MAYA_VER} with mGear to use C++ acceleration."
else
    echo "  WARNING: Build completed but .so not found at expected location."
    echo "  Check ${BUILD_DIR} for the output file."
fi

echo ""
