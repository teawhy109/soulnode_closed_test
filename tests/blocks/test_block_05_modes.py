# tests/blocks/test_block_05_modes.py
from core_instructions import get_mode_instructions

def test_soul_mode_has_warmth_keywords():
    txt = get_mode_instructions("soul").lower()
    assert "tone" in txt
    assert "warmth" in txt or "empathy" in txt

def test_no_bullshit_mode_is_direct_and_avoids_belief_phrase():
    txt = get_mode_instructions("no_bullshit").lower()
    assert "no fluff" in txt
    assert ("direct" in txt) or ("unfiltered" in txt)
    # explicitly confirm the warning is present
    assert "do not say 'i believe in you'" in txt

def test_unknown_mode_falls_back_to_standard():
    txt = get_mode_instructions("unknown-mode").lower()
    assert "operate in standard executor mode" in txt
    assert "never break tone" in txt