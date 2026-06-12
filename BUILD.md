# How to Build mGear Solvers

## Prerequisites
Before compiling mGear solvers, ensure you have the following installed:

- **CMake** (latest version recommended)
- **Compiler**
  - Windows: Microsoft Visual Studio
  - Linux: GCC / Clang
  - macOS: Xcode
- **Maya Development Kit** (Maya SDK) for the respective version
- **C++ Build Tools**
- **CMake Generator** matching your platform
- Execute the following commands from the cmake folder where FindMaya.cmake is

## Windows
To generate the build solution for Visual Studio, run the following commands:

```sh
cmake -G "Visual Studio 16 2019" -A x64 -DMAYA_VERSION=2022 ../
cmake -G "Visual Studio 16 2019" -A x64 -DMAYA_VERSION=2023 ../
cmake -G "Visual Studio 16 2019" -A x64 -DMAYA_VERSION=2024 ../
cmake -G "Visual Studio 17 2022" -A x64 -DMAYA_VERSION=2025 ../
cmake -G "Visual Studio 17 2022" -A x64 -DMAYA_VERSION=2026 ../
cmake -G "Visual Studio 17 2022" -A x64 -DMAYA_VERSION=2027 ../
```

Or use the helper script which auto-detects the installed Maya SDK and picks the matching Visual Studio generator:

```bat
:: Auto-detect (Maya 2022-2027)
build_solvers.bat

:: Target a specific version
build_solvers.bat 2022

:: Clean build
build_solvers.bat clean 2022
```

To compile the solution:
```sh
cmake --build . --config Release
```

## Linux
For Linux, use Unix Makefiles as the generator:

```sh
cmake -G "Unix Makefiles" -DMAYA_VERSION=2025 ../
cmake --build . --config Release
```

## macOS
Use Xcode as the generator and specify the architecture:

```sh
cmake -G "Xcode" -DMAYA_VERSION=2024 -DCMAKE_OSX_ARCHITECTURES="x86_64;arm64" ../
cmake -G "Xcode" -DMAYA_VERSION=2025 -DCMAKE_OSX_ARCHITECTURES="x86_64;arm64" ../
```

If the compiler is not found, reset Xcode tools:
```sh
sudo xcode-select --reset
```

For Maya 2024 and later, you should compile a universal binary:
```sh
cmake -G "Xcode" -DMAYA_VERSION=2024 \
  -DCMAKE_OSX_ARCHITECTURES="x86_64;arm64" \
  -DMaya_DIR=/Applications/Autodesk/maya2024/Maya.app/Contents/ ../

cmake -G "Xcode" -DMAYA_VERSION=2025 \
  -DCMAKE_OSX_ARCHITECTURES="x86_64;arm64" \
  -DMaya_DIR=/Applications/Autodesk/maya2025/Maya.app/Contents/ ../

cmake -G "Xcode" -DMAYA_VERSION=2027 \
  -DCMAKE_OSX_ARCHITECTURES="x86_64;arm64" \
  -DMaya_DIR=/Applications/Autodesk/maya2027/Maya.app/Contents/ ../
```

### Checking Architecture
To verify that the compiled binary supports both architectures:
```sh
lipo -info mgear_solvers.bundle
```

## Additional Resources
- [Maya 2024 API Update Guide](https://around-the-corner.typepad.com/adn/2023/03/maya-2024-api-update-guide.html)
- [Maya 2025 API Update Guide](https://around-the-corner.typepad.com/adn/2024/03/maya-2025-api-update-guide.html)

