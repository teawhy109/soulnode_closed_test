import gradio as gr
import json

MEMORY_FILE = "soulnode_memory.json"

def final_recall_and_check(topic):
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory file found or invalid format."

    topic_lower = topic.lower()
    seen = set()
    results = []

    for entry in data:
        if entry.get("topic", "").lower() == topic_lower:
            response = entry.get("response", "")
            if response not in seen:
                seen.add(response)
                results.append(f"{entry.get('tone', '').upper()} → {response}")

    if not results:
        return f"No matching entries found for topic: {topic}"
    
    return "\n".join(results)

def launch_phase10_12():
    with gr.Blocks() as app:
        gr.Markdown("## SoulNode | Phase 10.12 – Final Recall & Duplicate Filter")

        topic_input = gr.Textbox(label="Enter Topic Tag")
        output = gr.Textbox(label="Unique Entries", lines=10)

        recall_btn = gr.Button("Recall Unique")

        recall_btn.click(fn=final_recall_and_check, inputs=topic_input, outputs=output)

    app.launch()

if __name__ == "__main__":
    launch_phase10_12()