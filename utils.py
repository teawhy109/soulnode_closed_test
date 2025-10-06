# utils.py
import json
from datetime import datetime
from pathlib import Path

# Where unknown inputs should get logged
LOG_FILE = Path("logs/unknown_inputs.log")


def save_memory(store, subj: str, rel: str, obj: str):
    """
    Wrapper to store a fact in memory_store
    and log what was saved.
    """
    try:
        store.remember(subj, rel, obj)
        print(f"[utils] Saved memory: {subj} - {rel} -> {obj}")
    except Exception as e:
        print("[utils] save_memory error:", e)


def log_unknown_input(q: str):
    """
    Append unrecognized questions to a log file for later review.
    """
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} - {q}\n")
        print(f"[utils] Logged unknown input: {q}")
    except Exception as e:
        print("[utils] log_unknown_input error:", e)
