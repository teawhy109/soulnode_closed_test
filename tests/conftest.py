# tests/conftest.py
import sys, os, pathlib

# Ensure project root is on sys.path so `import app` works in tests
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT)) # make pytest run as if from project root