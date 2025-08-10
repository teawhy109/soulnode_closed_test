import gradio as gr
from memory_engine_v2 import save_memory_entry

def log_memory(input_text, response_text, tone, topic):
    result = save_memory_entry(
        user_input=input_text,
        response=response_text,
        tone=tone,
        topic=topic
    )
    return result

def launch_phase10_2():
    with gr.Blocks(title="SoulNode | Phase 10.2 - Memory Logger Test") as app:
        gr.Markdown("### SoulNode | Phase 10.2 - Memory Logger Test")

        with gr.Row():
            input_text = gr.Textbox(label="User Input")
            response_text = gr.Textbox(label="SoulNode Response")

        with gr.Row():
            tone = gr.Textbox(label="Tone (e.g. Chill, Heart, Beast)")
            topic = gr.Textbox(label="Memory Topic (e.g. glucose, motivation, dadmode)")

        output = gr.Textbox(label="Log Result")

        submit_btn = gr.Button("Log Memory")
        submit_btn.click(
            fn=log_memory,
            inputs=[input_text, response_text, tone, topic],
            outputs=output
        )

    app.launch()

if __name__ == "__main__":
    launch_phase10_2()