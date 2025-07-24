from pathlib import Path
from dotenv import load_dotenv
import os
import time
import pygame
import requests
import openai
from tts_engine import speak_with_elevenlabs

# Load environment variables
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Load API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

# Clear stale mp3 and spoken.txt
if os.path.exists("response.mp3"):
    try:
        os.remove("response.mp3")
    except Exception as e:
        print(f"Could not delete response.mp3: {e}")

if os.path.exists("spoken.txt"):
    with open("spoken.txt", "w", encoding="utf-8") as f:
        f.write("")

# Voice loop
def speak_loop():
    last_spoken = ""
    while True:
        try:
            with open("spoken.txt", "r", encoding="utf-8") as f:
                text = f.read().strip()

            if text and text != last_spoken:
                speak_with_elevenlabs(text)
                last_spoken = text

        except Exception as e:
            print(f"Voice loop error: {e}")
        
        time.sleep(2)

if __name__ == "__main__":
    print("SoulNode Voice Loop Active. Type 'exit' in main.py to stop.")
    speak_loop()