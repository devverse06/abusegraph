from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "run_pipeline.py")], cwd=ROOT, check=True)
print("\nStart the demo with:")
print(f"  {sys.executable} demo/server.py")
print("Then open http://127.0.0.1:8000/demo/")
