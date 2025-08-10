import pyttsx3

def get_engine_settings(mode):
    engine = pyttsx3.init()
    
    # Default settings
    rate = 190
    volume = 1.0
    voice_index = 0 # Adjust if you want to change system voice

    if mode.lower() == "beast":
        rate = 220
        volume = 1.0
    elif mode.lower() == "chill":
        rate = 160
        volume = 0.8
    elif mode.lower() == "heart":
        rate = 170
        volume = 0.9
    else:
        rate = 190
        volume = 1.0

    engine.setProperty('rate', rate)
    engine.setProperty('volume', volume)

    voices = engine.getProperty('voices')
    if voices:
        engine.setProperty('voice', voices[voice_index].id)

    return engine

def speak_tone_response(text, mode="default"):
    engine = get_engine_settings(mode)
    engine.say(text)
    engine.runAndWait()

# Example manual test (delete or comment out after)
if __name__ == "__main__":
    speak_tone_response("SoulNode is now speaking in Beast Mode. Let's go!", mode="beast")
    speak_tone_response("SoulNode is now speaking from the heart. You got this.", mode="heart")
    speak_tone_response("SoulNode is now speaking in chill mode. Just breathe.", mode="chill")