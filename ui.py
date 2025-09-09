import gradio as gr
from soulnode_memory import SoulNodeMemory

memory = SoulNodeMemory()

def ask_memory(subject, relation):
    result = memory.ask(subject.strip(), relation.strip())
    return result if result else "I don't have a verified answer."

def save_memory(subject, relation, obj):
    success, msg = memory.save_fact(subject.strip(), relation.strip(), obj.strip())
    return msg

def clear_memory():
    memory.clear()
    return "Memory cleared."

def show_all():
    data = memory.export_all()
    return "\n".join([f"{k} → {v}" for k, v in data.items()]) if data else "Memory is empty."

with gr.Blocks() as demo:
    gr.Markdown("## 🧠 SoulNode Memory Interface")

    with gr.Tab("Ask"):
        subj = gr.Textbox(label="Subject")
        rel = gr.Textbox(label="Relation")
        ask_btn = gr.Button("Ask")
        output = gr.Textbox(label="Answer")
        ask_btn.click(ask_memory, inputs=[subj, rel], outputs=output)

    with gr.Tab("Save"):
        s = gr.Textbox(label="Subject")
        r = gr.Textbox(label="Relation")
        o = gr.Textbox(label="Object")
        save_btn = gr.Button("Save")
        save_result = gr.Textbox(label="Result")
        save_btn.click(save_memory, inputs=[s, r, o], outputs=save_result)

    with gr.Tab("Clear"):
        clear_btn = gr.Button("Clear Memory")
        clear_out = gr.Textbox(label="Clear Status")
        clear_btn.click(clear_memory, outputs=clear_out)

    with gr.Tab("Export"):
        export_btn = gr.Button("Show All Memory")
        export_box = gr.Textbox(label="Stored Facts")
        export_btn.click(show_all, outputs=export_box)

demo.launch()