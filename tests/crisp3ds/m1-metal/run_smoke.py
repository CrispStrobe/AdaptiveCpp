"""Bounded native Metal GPU JIT regression; writes only a new output directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--prefix", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
prefix = args.prefix.resolve()
source = Path(__file__).resolve().with_name("smoke.cpp")
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
compiler = prefix / "bin/acpp"
backend = prefix / "lib/hipSYCL/librt-backend-metal.dylib"
if not compiler.is_file() or not backend.is_file():
    parser.error("prefix must contain bin/acpp and native Metal backend")
args.output.mkdir(parents=True, exist_ok=False)
output = args.output.resolve()
env = dict(os.environ, ACPP_VISIBILITY_MASK="metal", OMP_NUM_THREADS="2",
           XDG_DATA_HOME=str(output / "runtime-cache"))
env["DYLD_LIBRARY_PATH"] = str(prefix / "lib") + ":" + env.get("DYLD_LIBRARY_PATH", "")
inputs = {str(source): sha(source), str(compiler): sha(compiler), str(backend): sha(backend)}
installed = {str(p): sha(p) for p in prefix.rglob("*") if p.is_file()}
commands = [("compile", [str(compiler), "--acpp-targets=generic", str(source), "-O2", "-o", str(output / "smoke")]),
            ("execute", [str(output / "smoke")])]
result = {"schema": "native_m1_metal_smoke_v1", "status": "running", "stages": [],
          "inputs_sha256": inputs, "target": "generic", "required_device": "Metal GPU",
          "required_capabilities": ["float32", "native Metal backend", "GPU execution"],
          "whole_pipeline_deadline_seconds": 120, "normals_verified": 1024,
          "no_CPU_fallback": True}
begin = time.monotonic()
try:
    for name, command in commands:
        start = time.monotonic()
        with (output / (name + ".log")).open("wb") as log:
            process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                process.wait(timeout=max(0.01, 120 - (time.monotonic() - begin)))
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise RuntimeError(f"{name} exceeded 120 seconds")
        result["stages"].append({"name": name, "command": command,
                                  "returncode": process.returncode, "seconds": time.monotonic() - start})
        if process.returncode:
            raise RuntimeError(f"{name} failed: {process.returncode}")
    text = (output / "execute.log").read_text()
    if "gpu=1; backend=metal; normals=1024;" not in text:
        raise RuntimeError("Metal GPU output verification marker missing")
    result["status"] = "native_metal_geometry_kernel_verified"
    result["executable_sha256"] = sha(output / "smoke")
except Exception as error:
    result.update(status="failed", error=str(error))
finally:
    result["inputs_unchanged"] = all(sha(Path(p)) == h for p, h in inputs.items())
    result["installed_files_unchanged"] = all(sha(Path(p)) == h for p, h in installed.items())
    result["installed_inventory_before"] = installed
    result["seconds"] = time.monotonic() - begin
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(result["status"])
raise SystemExit(0 if result["status"] == "native_metal_geometry_kernel_verified" and result["inputs_unchanged"] and result["installed_files_unchanged"] else 1)
