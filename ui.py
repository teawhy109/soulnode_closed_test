import gradio as gr
import requests
import tempfile

def play_voice_memory():
    try:
        print("Sending request to Flask /recall-voice...")
        response = requests.get("http://127.0.0.1:5000/recall-voice")
        print(f"Response status code: {response.status_code}")

        if response.status_code != 200:
            return "Error fetching voice memory."

        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_audio.write(response.content)
        temp_audio.close()
        print(f"Saved MP3 to: {temp_audio.name}")
        return temp_audio.name
    except Exception as e:
        print(f"Exception in UI: {e}")
        return f"Error: {str(e)}"

with gr.Blocks() as demo:
    gr.Markdown("### SoulNode Voice Recall")
    with gr.Row():
        recall_button = gr.Button("Recall Recent Memories")
    with gr.Row():
        audio_output = gr.Audio(label="Voice Output", type="filepath")

    recall_button.click(fn=play_voice_memory, outputs=audio_output)

demo.launch()