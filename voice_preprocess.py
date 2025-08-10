import os
import librosa
import soundfile as sf
import numpy as np

INPUT_PATH = "voice_data/input"
OUTPUT_PATH = "voice_data/output"

def normalize_audio(y):
    return y / np.max(np.abs(y))

def trim_silence(y, top_db=20):
    return librosa.effects.trim(y, top_db=top_db)[0]

def preprocess_audio(filename):
    input_file = os.path.join(INPUT_PATH, filename)
    output_file = os.path.join(OUTPUT_PATH, filename)

    y, sr = librosa.load(input_file, sr=None)
    y = normalize_audio(y)
    y = trim_silence(y)

    sf.write(output_file, y, sr)
    print(f"[] Preprocessed: {filename} → Saved to output.")

if __name__ == "__main__":
    for filename in os.listdir(INPUT_PATH):
        if filename.endswith(".wav"):
            preprocess_audio(filename)