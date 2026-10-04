# Darwin generic CPU JIT backport

This branch starts at AdaptiveCpp v25.10.0 (`9f842c701a599107cc6d117d3539f971036363a1`).
The linker commit adds the tested Xcode SDK `-syslibroot` and `-lSystem` to the
Darwin host JIT invocation. Without them, generated host libraries lacked the
required system runtime linkage. The source is byte-identical to the tested
Apple Silicon CPU installation. This is not a Metal backend implementation;
the separate newer upstream develop Metal build is untouched.

The SDK pathname in this backport is deliberately the exact tested full-Xcode
pathname. Other SDK layouts require a separately tested change; the scripts
below are portable between checkout and installation directories, but this
linker patch does not claim universal SDK discovery.

## Build

Use matching LLVM/LLD 20.1.8, Boost and libomp. The tested configuration used
Homebrew on Apple Silicon, libc++, Ninja, and the full compiler feature profile:

```sh
cmake -S . -B build-darwin-host -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PWD/install-darwin-host" \
  -DCMAKE_OSX_SYSROOT="$(xcrun --sdk macosx --show-sdk-path)" \
  -DCMAKE_C_COMPILER=/opt/homebrew/opt/llvm@20/bin/clang \
  -DCMAKE_CXX_COMPILER=/opt/homebrew/opt/llvm@20/bin/clang++ \
  -DLLVM_DIR=/opt/homebrew/opt/llvm@20/lib/cmake/llvm \
  -DCLANG_EXECUTABLE_PATH=/opt/homebrew/opt/llvm@20/bin/clang++ \
  -DACPP_LLD_PATH=/opt/homebrew/opt/lld@20/bin/ld64.lld \
  -DACPP_COMPILER_FEATURE_PROFILE=full \
  -DOpenMP_ROOT=/opt/homebrew/opt/libomp \
  -DWITH_OPENCL_BACKEND=OFF -DWITH_CUDA_BACKEND=OFF -DWITH_ROCM_BACKEND=OFF
cmake --build build-darwin-host --parallel 2
cmake --install build-darwin-host
```

Verify that `xcrun` reports the SDK pathname embedded in `LLVMToHost.cpp`.
No package installation or build occurs automatically.

## Regression

```sh
python3 tests/crisp3ds/darwin-host-jit/verify_source.py
python3 tests/crisp3ds/darwin-host-jit/run_smoke.py \
  --prefix "$PWD/install-darwin-host" --output "$PWD/smoke-darwin-host"
```

The runner requires a fresh output directory, forces the OpenMP CPU device,
uses a fresh JIT cache, bounds each subprocess to 120 seconds, and preserves
logs plus a result receipt. Its kernel verifies all 1024 double outputs and
requires FP64 and host/device USM support. A device query alone is insufficient.
`evidence.json` records source and historical validation hashes; no binaries,
private paths, credentials or image datasets are committed.
