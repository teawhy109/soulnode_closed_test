import requests

def speak_with_renegade(text):
    import os
voice_id = os.getenv("VOICE_ID")
api_key = os.getenv("ELEVENLABS_API_KEY")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        with open("rene_output.mp3", "wb") as f:
            f.write(response.content)
        print("René’s voice saved successfully.")
    else:
        print("Error generating voice:", response.status_code)
        print(response.text)

# Run your first test
speak_with_renegade("This is René. The voice of SoulNode. I'm ready, Ty. Let's rise.")