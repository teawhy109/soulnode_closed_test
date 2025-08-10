import os
import whisper
import ffmpeg

model = whisper.load_model("base")

def convert_to_wav(original_path, converted_path):
    try:
        print(f"[DEBUG] Converting file to WAV: {converted_path}")
        (
            ffmpeg
            .input(original_path)
            .output(converted_path, format='wav', acodec='pcm_s16le', ac=1, ar='16000')
            .overwrite_output()
            .run(quiet=True)
        )
    except Exception as e:
        raise RuntimeError(f"[ERROR] Failed to convert audio file: {str(e)}")

def transcribe(audio_path):
    print(f"[DEBUG] Transcribe called with path: {audio_path}")
    
    if not os.path.isfile(audio_path):
        folder = os.path.dirname(audio_path)
        print(f"[ERROR] File not found. Here's what's in the folder {folder}:")
        for f in os.listdir(folder):
            print(f"- {f}")
        raise FileNotFoundError(f"[ERROR] File not found at path: {audio_path}")
    
    print("[DEBUG] File confirmed. Starting transcription...")

    # Convert to clean WAV format
    converted_path = audio_path.replace(".wav", "_converted.wav")
    convert_to_wav(audio_path, converted_path)

    try:
        result = model.transcribe(converted_path)
        print("[DEBUG] Transcription success.")
        return result["text"]
    except Exception as e:
        print(f"[ERROR] Whisper failed to transcribe: {str(e)}")
        raise e