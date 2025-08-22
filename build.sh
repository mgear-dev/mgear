#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e


cmake -G "Xcode" -DMAYA_VERSION=2026 \
  -DCMAKE_OSX_ARCHITECTURES="x86_64;arm64" \
  -DMaya_DIR=/Applications/Autodesk/maya2026/Maya.app/Contents/ \
  -DCMAKE_CXX_STANDARD=11 \
  -DCMAKE_CXX_STANDARD_REQUIRED=ON

cmake --build . --config Release
