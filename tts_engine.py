import requests
import os
import pygame
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

def speak_with_elevenlabs(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.8
        }
    }

    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        file_path = "response.mp3"
        
        # If the file already exists and is locked, force unload it
        if os.path.exists(file_path):
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete old mp3: {e}")
        
        with open(file_path, "wb") as f:
            f.write(response.content)

        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            continue

        pygame.mixer.music.stop()
        pygame.mixer.quit()
    else:
        print(f"Voice generation failed: {response.status_code} - {response.text}")