import os
import numpy as np
import librosa

INPUT_PATH = "voice_data/output"
EMBED_PATH = "voice_data/temp/voice_embedding.npy"

def extract_embedding(audio_path):
    y, sr = librosa.load(audio_path, sr=None)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    return np.mean(mfcc.T, axis=0)

def normalize_embedding(embedding):
    norm = np.linalg.norm(embedding)
    if norm == 0:
        return embedding
    return embedding / norm

if __name__ == "__main__":
    wav_files = [f for f in os.listdir(INPUT_PATH) if f.endswith(".wav")]
    if not wav_files:
        print("No WAV files found in output folder.")
    else:
        wav_file = os.path.join(INPUT_PATH, wav_files[0])
        embedding = extract_embedding(wav_file)
        embedding = normalize_embedding(embedding)
        embedding = embedding.astype("float32")
        with open(EMBED_PATH, 'wb') as f:
            np.save(f, embedding, allow_pickle=False)
        print(f"Voice embedding saved to {EMBED_PATH}")