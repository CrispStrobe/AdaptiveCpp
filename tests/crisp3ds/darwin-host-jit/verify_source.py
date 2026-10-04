from pathlib import Path
import hashlib
root = Path(__file__).resolve().parents[3]
source = root / "src/compiler/llvm-to-backend/host/LLVMToHost.cpp"
expected = "2ef6a6e9ab7d1d758957ad1f0220ad5cbaf7d13e8a6a962bec7bac8cdb3e1139"
actual = hashlib.sha256(source.read_bytes()).hexdigest()
if actual != expected:
    raise SystemExit(f"Source differs from tested linker patch: {actual}")
print(f"Exact tested linker source verified: {actual}")
