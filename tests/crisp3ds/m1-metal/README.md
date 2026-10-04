# Build current upstream Metal support on Apple M1

Pinned upstream AdaptiveCpp: `a215fbcd89087d638769c0a0449bc2abb9350f8e`.
Pinned official Apple metal-cpp: `27c4382b7151d55a51692cdcb27aaa98752240de`.
Both matched the official upstream HEADs checked on 2026-10-04. Runtime and
compiler source on this branch are unchanged from that AdaptiveCpp revision.

The tested machine used Apple M1, macOS 26, full Xcode, LLVM/LLD 20.1.8,
Boost and libomp. This experimental Metal backend requires float device code;
FP64 and 64-bit atomics are unsupported. Read [upstream Metal limitations](../../../doc/install-metal.md).

## Configure and build

Install compatible dependencies separately. These commands perform no package
manager updates or automatic installs. The paths below are parameters, rather
than another developer's home directory. Supply the same LLVM/LLD version for
reproducing the tested toolchain.

```sh
git clone --branch crisp3ds/m1-metal https://github.com/CrispStrobe/AdaptiveCpp.git
cd AdaptiveCpp
git clone https://github.com/apple/metal-cpp.git metal-cpp
git -C metal-cpp checkout --detach 27c4382b7151d55a51692cdcb27aaa98752240de
LLVM_PREFIX="$(brew --prefix llvm@20)"
LLD_PREFIX="$(brew --prefix lld@20)"
OMP_PREFIX="$(brew --prefix libomp)"
SDK_PATH="$(xcrun --sdk macosx --show-sdk-path)"
INSTALL_PREFIX="$PWD/install-m1-metal"
METAL_CPP_PATH="$PWD/metal-cpp"
cmake -S . -B build-m1-metal -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_SYSROOT="$SDK_PATH" \
  -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
  -DCMAKE_CXX_COMPILER="$LLVM_PREFIX/bin/clang++" \
  -DCMAKE_C_COMPILER="$LLVM_PREFIX/bin/clang" \
  -DLLVM_DIR="$LLVM_PREFIX/lib/cmake/llvm" \
  -DCLANG_EXECUTABLE_PATH="$LLVM_PREFIX/bin/clang++" \
  -DACPP_LLD_PATH="$LLD_PREFIX/bin/ld64.lld" \
  -DACPP_COMPILER_FEATURE_PROFILE=full \
  -DOpenMP_ROOT="$OMP_PREFIX" \
  -DWITH_OPENCL_BACKEND=OFF -DWITH_CUDA_BACKEND=OFF -DWITH_ROCM_BACKEND=OFF \
  -DWITH_METAL_BACKEND=ON -DMETAL_INCLUDE_DIR="$METAL_CPP_PATH"
cmake --build build-m1-metal --parallel 2
cmake --install build-m1-metal
```

This matches the frozen tested full-profile configuration, with machine paths
parameterized. The explicit metal-cpp checkout avoids a moving release branch.
CMake's LLVM major version must match the selected compiler and linker.

## Actual GPU regression

```sh
python3 tests/crisp3ds/m1-metal/run_smoke.py \
  --prefix "$INSTALL_PREFIX" --output "$PWD/metal-smoke-001"
```

Use a fresh output directory each time. The runner freezes input/source and
installed-file hashes, compiles through `acpp --acpp-targets=generic`, uses a
fresh JIT cache, forces `ACPP_VISIBILITY_MASK=metal`, and bounds the whole
compile/execute sequence to 120 seconds. A timeout terminates its owned process
group; logs and the failure receipt remain available.

The kernel requires `is_gpu()` and `backend::metal`; a CPU device fails even
if it could calculate correct values. It computes 1,024 float cross products,
normalizations and dot products, checking finite output against an independent
host-double calculation with maximum error at most `1e-5`. This demonstrates
native GPU computation, not just a device listing. It is not an object-mesh
quality test or a performance benchmark. `evidence.json` records the actual
validation against the current immutable installed build; no new runtime
source changes or rebuilt fork binaries are claimed.
