# tests/blocks/test_block_09_intent_mapping.py
# Contract test: response_map.get_response_for_prompt returns a usable string
# for known phrases (from intent_map.json) and for unknown input.

import json
import pathlib
import importlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
intent_path = ROOT / "intent_map.json"

def test_response_map_contract_on_known_phrases():
    response_map = importlib.import_module("response_map")
    assert hasattr(response_map, "get_response_for_prompt") and callable(response_map.get_response_for_prompt)

    data = json.loads(intent_path.read_text(encoding="utf-8"))
    # Pick one sample phrase per intent bucket (keeps test fast/deterministic)
    samples = []
    for k, v in data.items():
        if isinstance(v, list) and v:
            samples.append(v[0])

    # Sanity: we found some samples
    assert samples, "intent_map.json appears empty"

    # For each phrase, the mapper must return a non-empty string
    for phrase in samples:
        out = response_map.get_response_for_prompt(phrase)
        assert isinstance(out, str)
        assert out.strip() != ""

def test_response_map_handles_unknown_phrase():
    response_map = importlib.import_module("response_map")
    out = response_map.get_response_for_prompt("this phrase should not exist in the map 9e1b942e")
    assert isinstance(out, str)
    assert out.strip() != ""