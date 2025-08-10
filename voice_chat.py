import os
import openai
import requests
from pydub import AudioSegment
from dotenv import load_dotenv
import whisper
from uuid import uuid4

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

whisper_model = whisper.load_model("base")

def transcribe_audio(file_path):
    result = whisper_model.transcribe(file_path)
    return result["text"]

def generate_ai_response(prompt):
    messages = [
        {"role": "system", "content": "You're a soulful AI assistant named SoulNode."},
        {"role": "user", "content": prompt}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages
    )
    return response.choices[0].message.content

def convert_text_to_speech(text, voice_id="EXAVITQu4vr4xnSDxMaL"):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.7
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        filename = f"response_{uuid4().hex}.mp3"
        with open(filename, "wb") as f:
            f.write(response.content)
        return filename
    else:
        raise Exception(f"ElevenLabs error: {response.status_code} - {response.text}")