# profiles.py

USER_PROFILES = {
    "Ty_Commander": {
        "name": "Ty Butler",
        "role": "Founder",
        "mode": "Tactical",
        "theme": "dark",
        "voice": "SoNoVox_Main",
        "monologue": "Welcome back, Ty. Ready to execute?"
    },
    "Nana_Pam": {
        "name": "Pamlea Butler",
        "role": "Mom",
        "mode": "Soul",
        "theme": "light",
        "voice": "SoNoVox_Nana",
        "monologue": "Hi sweetheart, I'm here to talk. What would you like to hear today?"
    },
    "Default": {
        "name": "Guest",
        "role": "User",
        "mode": "Neutral",
        "theme": "light",
        "voice": "None",
        "monologue": "Hello. I'm SoulNode, your AI assistant."
    }
}

def get_user_profile(user_key):
    return USER_PROFILES.get(user_key, USER_PROFILES["Default"])