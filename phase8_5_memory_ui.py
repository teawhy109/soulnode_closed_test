import gradio as gr
import json

MEMORY_FILE = "memorystore.json"

def search_memory(query):
    try:
        with open(MEMORY_FILE, "r") as f:
            memory_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory file found or file is corrupted."

    results = []
    query_lower = query.lower()

    for entry in memory_data:
        if isinstance(entry, dict):
            input_text = entry.get("input", "").lower()
            if query_lower in input_text:
                results.append(entry)

    if results:
        return json.dumps(results, indent=2)
    else:
        return "No matching entries found."

def launch_phase8_5():
    with gr.Blocks(title="SoulNode | Phase 8.5 Tactical Memory Recall") as app:
        gr.Markdown("## 🔍 SoulNode | Phase 8.5 Tactical Memory Recall")

        with gr.Row():
            query = gr.Textbox(label="Search Phrase")
            output = gr.Textbox(label="Search Results")

        search_btn = gr.Button("Search")
        search_btn.click(fn=search_memory, inputs=query, outputs=output)

    app.launch()

if __name__ == "__main__":
    launch_phase8_5()