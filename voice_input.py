import tempfile
import os
import whisper

def transcribe_audio(file):
    print("Received file:", file.filename)

    try:
        model = whisper.load_model("base")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
            file.save(temp.name)
            temp_path = temp.name

        print("Temp path:", temp_path)
        print("File exists?", os.path.exists(temp_path))
        print("File size:", os.path.getsize(temp_path) if os.path.exists(temp_path) else "File not found")

        result = model.transcribe(temp_path)
        return result["text"]

    except Exception as e:
        print("Error during transcription:", str(e))
        return {"error": str(e)}