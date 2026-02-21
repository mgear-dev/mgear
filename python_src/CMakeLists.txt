cmake_minimum_required(VERSION 3.16)
project(rgp_accel LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --------------------------------------------------------------------------
# Maya Python -- Maya bundles Python in a non-standard layout.
#
# Windows:
#   MAYA_ROOT = C:/Program Files/Autodesk/Maya2026
#   include/Python3XX/Python/Python.h
#   lib/python3XX.lib
#   bin/python3XX.dll
#   bin/mayapy.exe
#
# Linux:
#   MAYA_ROOT = /usr/autodesk/maya2026
#   include/Python3XX/Python/Python.h
#   lib/libpython3.XXm?.so  (or libpython3.XX.so)
#   bin/mayapy
#
# macOS:
#   MAYA_ROOT = /Applications/Autodesk/maya2026/Maya.app/Contents
#   include/Python3XX/Python/Python.h
#   lib/libpython3.XX.dylib  (or Frameworks/Python.framework/...)
#   bin/mayapy
#
# Usage:
#   cmake .. -DMAYA_ROOT="C:/Program Files/Autodesk/Maya2026"      (Windows)
#   cmake .. -DMAYA_ROOT="/usr/autodesk/maya2026"                   (Linux)
#   cmake .. -DMAYA_ROOT="/Applications/Autodesk/maya2026/Maya.app/Contents"  (macOS)
# --------------------------------------------------------------------------
if(NOT MAYA_ROOT)
    message(FATAL_ERROR
        "Set -DMAYA_ROOT to your Maya install, e.g.:\n"
        "  cmake .. -DMAYA_ROOT=\"C:/Program Files/Autodesk/Maya2026\"  (Windows)\n"
        "  cmake .. -DMAYA_ROOT=\"/usr/autodesk/maya2026\"              (Linux)\n"
        "  cmake .. -DMAYA_ROOT=\"/Applications/Autodesk/maya2026/Maya.app/Contents\"  (macOS)")
endif()

# Auto-detect the Python version Maya ships (3.9, 3.10, 3.11 ...)
file(GLOB _maya_pyinc_dirs "${MAYA_ROOT}/include/Python3*")
list(LENGTH _maya_pyinc_dirs _n_pyinc)
if(_n_pyinc EQUAL 0)
    message(FATAL_ERROR "No Python include dir found under ${MAYA_ROOT}/include/Python3*")
endif()
# Pick the first (usually only one)
list(GET _maya_pyinc_dirs 0 _maya_pyinc_dir)
get_filename_component(_pyver_tag "${_maya_pyinc_dir}" NAME)   # e.g. "Python311"
string(REGEX REPLACE "Python([0-9]+)" "\\1" _pyver_digits "${_pyver_tag}")  # "311"

set(MAYA_PYTHON_INCLUDE "${_maya_pyinc_dir}/Python")

# Derive version string (e.g. "311" -> "3.11")
string(SUBSTRING "${_pyver_digits}" 0 1 _py_major)
string(SUBSTRING "${_pyver_digits}" 1 -1 _py_minor)
set(MAYA_PYTHON_VERSION "${_py_major}.${_py_minor}")

# --------------------------------------------------------------------------
# Platform-specific Python library and executable detection
# --------------------------------------------------------------------------
if(WIN32)
    set(MAYA_PYTHON_LIB "${MAYA_ROOT}/lib/python${_pyver_digits}.lib")
    set(MAYA_PYTHON_DLL "${MAYA_ROOT}/bin/python${_pyver_digits}.dll")
    set(MAYA_PYTHON_EXE "${MAYA_ROOT}/bin/mayapy.exe")
    set(PYTHON_MODULE_EXTENSION ".cp${_pyver_digits}-win_amd64.pyd")

elseif(APPLE)
    # macOS: MAYA_ROOT should be .../Maya.app/Contents
    # Try lib/libpython3.XX.dylib first, then Frameworks
    set(_pyver_dotted "${_py_major}.${_py_minor}")
    set(_pylib_candidates
        "${MAYA_ROOT}/lib/libpython${_pyver_dotted}.dylib"
        "${MAYA_ROOT}/Frameworks/Python.framework/Versions/${_pyver_dotted}/lib/libpython${_pyver_dotted}.dylib"
    )
    set(MAYA_PYTHON_LIB "")
    foreach(_candidate ${_pylib_candidates})
        if(EXISTS "${_candidate}")
            set(MAYA_PYTHON_LIB "${_candidate}")
            break()
        endif()
    endforeach()
    if(NOT MAYA_PYTHON_LIB)
        # Glob as fallback
        file(GLOB _pylib_glob "${MAYA_ROOT}/lib/libpython3*.dylib")
        if(_pylib_glob)
            list(GET _pylib_glob 0 MAYA_PYTHON_LIB)
        endif()
    endif()
    set(MAYA_PYTHON_EXE "${MAYA_ROOT}/bin/mayapy")
    # macOS: Python extensions use .so (not .dylib) for importable modules
    set(PYTHON_MODULE_EXTENSION ".cpython-${_pyver_digits}-darwin.so")

else()
    # Linux
    set(_pyver_dotted "${_py_major}.${_py_minor}")
    set(_pylib_candidates
        "${MAYA_ROOT}/lib/libpython${_pyver_dotted}.so"
        "${MAYA_ROOT}/lib/libpython${_pyver_dotted}m.so"
    )
    set(MAYA_PYTHON_LIB "")
    foreach(_candidate ${_pylib_candidates})
        if(EXISTS "${_candidate}")
            set(MAYA_PYTHON_LIB "${_candidate}")
            break()
        endif()
    endforeach()
    if(NOT MAYA_PYTHON_LIB)
        # Glob as fallback
        file(GLOB _pylib_glob "${MAYA_ROOT}/lib/libpython3*.so")
        if(_pylib_glob)
            list(GET _pylib_glob 0 MAYA_PYTHON_LIB)
        endif()
    endif()
    set(MAYA_PYTHON_EXE "${MAYA_ROOT}/bin/mayapy")
    # Detect architecture for module suffix
    execute_process(
        COMMAND uname -m
        OUTPUT_VARIABLE _arch
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    set(PYTHON_MODULE_EXTENSION ".cpython-${_pyver_digits}-${_arch}-linux-gnu.so")
endif()

message(STATUS "Maya root     : ${MAYA_ROOT}")
message(STATUS "Platform      : ${CMAKE_SYSTEM_NAME}")
message(STATUS "Python tag    : ${_pyver_tag} (${_pyver_digits})")
message(STATUS "Python version: ${MAYA_PYTHON_VERSION}")
message(STATUS "Python include: ${MAYA_PYTHON_INCLUDE}")
message(STATUS "Python lib    : ${MAYA_PYTHON_LIB}")
message(STATUS "Module ext    : ${PYTHON_MODULE_EXTENSION}")

if(NOT EXISTS "${MAYA_PYTHON_INCLUDE}/Python.h")
    message(FATAL_ERROR "Python.h not found at ${MAYA_PYTHON_INCLUDE}/Python.h")
endif()
if(NOT MAYA_PYTHON_LIB OR NOT EXISTS "${MAYA_PYTHON_LIB}")
    message(FATAL_ERROR
        "Python library not found. Searched for:\n"
        "  ${MAYA_ROOT}/lib/libpython${_py_major}.${_py_minor}[m].so|.dylib  (Linux/macOS)\n"
        "  ${MAYA_ROOT}/lib/python${_pyver_digits}.lib                        (Windows)")
endif()

# --------------------------------------------------------------------------
# Create imported targets so pybind11 can find Python
# --------------------------------------------------------------------------
add_library(Python3::Headers INTERFACE IMPORTED)
set_target_properties(Python3::Headers PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${MAYA_PYTHON_INCLUDE}"
)

add_library(Python3::Module SHARED IMPORTED)
if(WIN32)
    set_target_properties(Python3::Module PROPERTIES
        IMPORTED_IMPLIB   "${MAYA_PYTHON_LIB}"
        IMPORTED_LOCATION "${MAYA_PYTHON_DLL}"
        INTERFACE_INCLUDE_DIRECTORIES "${MAYA_PYTHON_INCLUDE}"
    )
else()
    set_target_properties(Python3::Module PROPERTIES
        IMPORTED_LOCATION "${MAYA_PYTHON_LIB}"
        INTERFACE_INCLUDE_DIRECTORIES "${MAYA_PYTHON_INCLUDE}"
    )
endif()

# Set variables for pybind11's NEW Python3 path (FindPython3)
set(Python3_INCLUDE_DIRS "${MAYA_PYTHON_INCLUDE}")
set(Python3_LIBRARIES    "${MAYA_PYTHON_LIB}")
set(Python3_FOUND TRUE)
set(Python3_VERSION "${MAYA_PYTHON_VERSION}")
set(Python3_VERSION_MAJOR ${_py_major})
set(Python3_VERSION_MINOR ${_py_minor})
set(PYTHON_IS_DEBUG FALSE)

# Set CACHE variables for pybind11's LEGACY FindPythonInterp / FindPythonLibs.
# Cache vars prevent CMake's Find modules from overwriting with wrong paths.
set(PYTHON_EXECUTABLE "${MAYA_PYTHON_EXE}" CACHE FILEPATH "" FORCE)
set(PYTHON_INCLUDE_DIR "${MAYA_PYTHON_INCLUDE}" CACHE PATH "" FORCE)
set(PYTHON_LIBRARY     "${MAYA_PYTHON_LIB}" CACHE FILEPATH "" FORCE)

set(PYTHON_INCLUDE_DIRS "${MAYA_PYTHON_INCLUDE}")
set(PYTHON_LIBRARIES    "${MAYA_PYTHON_LIB}")
set(PYTHONLIBS_FOUND TRUE)
set(PYTHONINTERP_FOUND TRUE)
set(PYTHON_VERSION_STRING "${MAYA_PYTHON_VERSION}")
set(PYTHON_VERSION_MAJOR ${_py_major})
set(PYTHON_VERSION_MINOR ${_py_minor})
set(PYBIND11_PYTHON_VERSION "${MAYA_PYTHON_VERSION}")
set(PYTHONLIBS_VERSION_STRING "${MAYA_PYTHON_VERSION}")
set(PYTHON_MODULE_PREFIX "")
set(PYTHON_MODULE_DEBUG_POSTFIX "")
set(PYTHON_IS_DEBUG FALSE)

# --------------------------------------------------------------------------
# Find pybind11
# Priority: 1) -Dpybind11_DIR=...  2) pip-installed  3) FetchContent
# --------------------------------------------------------------------------
find_package(pybind11 QUIET)
if(NOT pybind11_FOUND)
    message(STATUS "pybind11 not found locally -- fetching from GitHub")
    include(FetchContent)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG        v2.12.0
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# --------------------------------------------------------------------------
# Build the extension module
# --------------------------------------------------------------------------
pybind11_add_module(_rgp_accel_cpp
    src/rgp_accel.cpp
    src/bindings.cpp
)

target_include_directories(_rgp_accel_cpp PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${MAYA_PYTHON_INCLUDE}
)

target_link_libraries(_rgp_accel_cpp PRIVATE
    "${MAYA_PYTHON_LIB}"
)

# Optimisation flags
if(MSVC)
    target_compile_options(_rgp_accel_cpp PRIVATE /O2 /fp:fast)
else()
    target_compile_options(_rgp_accel_cpp PRIVATE -O3 -ffast-math)
endif()

# --------------------------------------------------------------------------
# Output the module into release/scripts/mgear/shifter/ so Python can
# import it as mgear.shifter._rgp_accel_cpp
# --------------------------------------------------------------------------
set_target_properties(_rgp_accel_cpp PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../release/scripts/mgear/shifter"
    LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}/../release/scripts/mgear/shifter"
    LIBRARY_OUTPUT_DIRECTORY_DEBUG "${CMAKE_CURRENT_SOURCE_DIR}/../release/scripts/mgear/shifter"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../release/scripts/mgear/shifter"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_CURRENT_SOURCE_DIR}/../release/scripts/mgear/shifter"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_CURRENT_SOURCE_DIR}/../release/scripts/mgear/shifter"
)
