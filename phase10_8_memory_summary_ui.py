import gradio as gr
import json

MEMORY_FILE = "soulnode_memory.json"

def summarize_topic(topic):
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory file found."

    topic_lower = topic.lower()
    entries = [entry["response"] for entry in data if entry.get("topic", "").lower() == topic_lower]

    if not entries:
        return "No entries found for this topic."

    # Simple summarization by combining and deduplicating phrases
    combined = " ".join(set(entries))
    return f"Summary for topic '{topic}': {combined}"

def launch_phase10_8():
    with gr.Blocks() as app:
        gr.Markdown("### SoulNode | Phase 10.8 – Memory Cluster Summarizer")

        with gr.Row():
            topic_input = gr.Textbox(label="Enter Topic")
            summary_output = gr.Textbox(label="Summarized Insight")

        summarize_btn = gr.Button("Summarize Topic")
        summarize_btn.click(fn=summarize_topic, inputs=topic_input, outputs=summary_output)

    app.launch()

if __name__ == "__main__":
    launch_phase10_8()