from elevenlabs import ElevenLabs, Voice, VoiceSettings
from elevenlabs import ElevenLabs, Voice, VoiceSettings, play

client = ElevenLabs(api_key="sk_498764060e90766b490de3d8f9116b25e0072916af6039de")

def speak(text):
    audio = client.generate(
        text=text,
        voice=Voice(
            voice_id="EXAVITQu4vr4xnSDxMaL", # Default ElevenLabs voice ID
            settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75
            )
        )
    )
    play(audio)