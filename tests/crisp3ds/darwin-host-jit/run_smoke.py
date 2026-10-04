"""Bounded generic CPU JIT regression; writes only a new output directory."""
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
if not compiler.is_file():
    parser.error("prefix must contain bin/acpp")
args.output.mkdir(parents=True, exist_ok=False)
output = args.output.resolve()
env = dict(os.environ, ACPP_VISIBILITY_MASK="omp", OMP_NUM_THREADS="2",
           XDG_DATA_HOME=str(output / "runtime-cache"))
env["DYLD_LIBRARY_PATH"] = str(prefix / "lib") + ":" + env.get("DYLD_LIBRARY_PATH", "")
inputs = {str(source): sha(source), str(compiler): sha(compiler)}
commands = [("compile", [str(compiler), "--acpp-targets=generic", str(source), "-o", str(output / "smoke")]),
            ("execute", [str(output / "smoke")])]
result = {"schema": "darwin_generic_cpu_smoke_v1", "status": "running", "stages": [],
          "inputs_sha256": inputs, "target": "generic", "required_device": "CPU",
          "required_capabilities": ["fp64", "usm_device_allocations", "usm_host_allocations"],
          "deadline_seconds_per_stage": 120, "outputs_verified": 1024,
          "does_not_test_Metal": True}
try:
    for name, command in commands:
        start = time.monotonic()
        with (output / (name + ".log")).open("wb") as log:
            process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                process.wait(timeout=120)
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
    if "verified 1024 double outputs; CPU=" not in text:
        raise RuntimeError("CPU output verification marker missing")
    result["status"] = "generic_cpu_kernel_verified"
    result["executable_sha256"] = sha(output / "smoke")
except Exception as error:
    result.update(status="failed", error=str(error))
finally:
    result["inputs_unchanged"] = all(sha(Path(p)) == h for p, h in inputs.items())
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(result["status"])
raise SystemExit(0 if result["status"] == "generic_cpu_kernel_verified" and result["inputs_unchanged"] else 1)
