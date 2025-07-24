import gradio as gr
import requests

def talk_to_rene(message):
    response = requests.post("http://127.0.0.1:5000/ask_rene", json={"input": message})
    return response.json().get("response", "Something went wrong.")

iface = gr.Interface(
    fn=talk_to_rene,
    inputs="text",
    outputs="text",
    title="SoulNode: Ask René",
    description="This is your AI co-pilot. Ask away."
)

iface.launch()