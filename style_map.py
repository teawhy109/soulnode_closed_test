style_map = {
    "from the heart": "Heart",
    "beast mode": "Beast Mode",
    "keep it chill": "Real Chill"
}

def detect_style(user_input):
    for phrase, tone in style_map.items():
        if phrase in user_input.lower():
            return tone
    return "Tactical"