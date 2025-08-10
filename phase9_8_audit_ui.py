import gradio as gr
import json

MEMORY_FILE = "spoken_memory.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        return []

def format_memory():
    data = load_memory()
    if not data:
        return "No memory entries found."
    
    lines = []
    for idx, entry in enumerate(data, 1):
        lines.append(f"{idx}. Input: {entry.get('input')}")
        lines.append(f" Response: {entry.get('response')}")
        lines.append(f" Tone: {entry.get('tone')}")
        lines.append(f" Topic: {entry.get('topic')}")
        lines.append("")

    return "\n".join(lines)

def delete_memory_entry(index):
    data = load_memory()
    if not data or index < 1 or index > len(data):
        return "Invalid index."
    
    deleted = data.pop(index - 1)
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

    return f"Deleted entry {index}: {deleted.get('input')}"

def launch_phase9_8():
    with gr.Blocks(title="SoulNode | Phase 9.8 - Memory Audit & Cleanup") as app:
        gr.Markdown("## SoulNode | Phase 9.8 - Memory Audit & Cleanup Tools")

        memory_display = gr.Textbox(label="Current Memory Store", lines=25, interactive=False)

        index_input = gr.Number(label="Enter Entry # to Delete", value=1)
        delete_btn = gr.Button("Delete Entry")
        delete_result = gr.Textbox(label="Result")

        load_btn = gr.Button("Refresh Memory View")

        load_btn.click(fn=format_memory, outputs=memory_display)
        delete_btn.click(fn=delete_memory_entry, inputs=index_input, outputs=delete_result)

    app.launch()

if __name__ == "__main__":
    launch_phase9_8()