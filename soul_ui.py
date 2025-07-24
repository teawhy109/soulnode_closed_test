import gradio as gr
import requests

def ask_soulnode(user_input):
    try:
        response = requests.post(
            "http://127.0.0.1:5000/ask_rene",
            json={"input": user_input}
        )
        data = response.json()
        return data.get("response", "No response from SoulNode.")
    except Exception as e:
        return f"Error: {str(e)}"

with gr.Blocks(css=".avatar {text-align: center; margin-bottom: 10px;} .avatar img {width: 100px; border-radius: 100%;} .chatbot {min-height: 450px;}") as demo:
    
    with gr.Column():
        gr.Markdown("<h2 style='text-align: center;'>SoulNode Interface</h2>")
        
        with gr.Row():
            gr.HTML(
                """
                <div class="avatar">
                    <img src="https://i.imgur.com/8fKQ3QF.png" alt="SoulNode Avatar">
                </div>
                """)
        
        chatbot = gr.Chatbot(elem_classes="chatbot")
        msg = gr.Textbox(label="Type to SoulNode", placeholder="Ask anything...")

        clear = gr.Button("Clear")

        def respond(message, chat_history):
            response = ask_soulnode(message)
            chat_history.append((message, response))
            return "", chat_history

        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        clear.click(lambda: None, None, chatbot, queue=False)

demo.launch()