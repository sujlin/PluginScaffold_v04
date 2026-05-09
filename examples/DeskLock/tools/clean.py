#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]

for name in ("build", "dist"):
    path = ROOT / name
    if path.exists():
        shutil.rmtree(path)
        print(f"removed {path}")
    path.mkdir(parents=True, exist_ok=True)
    print(f"created {path}")
