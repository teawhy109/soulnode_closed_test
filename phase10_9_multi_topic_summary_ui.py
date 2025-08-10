import gradio as gr
import json

TAG_FILE = "soulnode_memory.json"

def summarize_multiple_topics(topics_input):
    try:
        with open(TAG_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory available."

    if not data:
        return "Memory is empty."

    topic_list = [topic.strip().lower() for topic in topics_input.split(",")]
    summaries = {}

    for entry in data:
        topic = entry.get("topic", "").lower()
        if topic in topic_list:
            if topic not in summaries:
                summaries[topic] = []
            summaries[topic].append(entry.get("response", ""))

    if not summaries:
        return "No matches found for the entered topics."

    output = ""
    for topic, responses in summaries.items():
        compressed = " / ".join(set(responses))
        output += f"Summary for '{topic}': {compressed}\n\n"

    return output.strip()

def launch_phase10_9():
    with gr.Blocks(title="SoulNode | Phase 10.9 - Multi-Topic Summary Recall") as app:
        gr.Markdown("### SoulNode | Multi-Topic Summary Recall")
        topic_input = gr.Textbox(label="Enter Topics (comma-separated)")
        result_output = gr.Textbox(label="Summary", lines=8)

        recall_btn = gr.Button("Recall Multi-Topic Summary")
        recall_btn.click(fn=summarize_multiple_topics, inputs=topic_input, outputs=result_output)

    app.launch()

if __name__ == "__main__":
    launch_phase10_9()