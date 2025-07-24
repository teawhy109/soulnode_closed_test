import gradio as gr
from main import ask_rene

def chat_with_soulnode(user_input):
    if not user_input.strip():
        return "Please enter a question or message."
    
    try:
        response = ask_rene(user_input)
        return response
    except Exception as e:
        return f"Error: {str(e)}"

iface = gr.Interface(
    fn=chat_with_soulnode,
    inputs=gr.Textbox(lines=2, placeholder="Ask SoulNode anything..."),
    outputs="text",
    title="SoulNode Interface",
    description="Your AI co-pilot for reflection, clarity, and execution.",
    theme="soft",
    allow_flagging="never"
)

if __name__ == "__main__":
    iface.launch()