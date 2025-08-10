import gradio as gr
import json
from logic import summarize_ranked_results
from memory_engine_v2 import save_memory_entry

MEMORY_FILE = "soulnode_memory.json"

def summarize_and_log(topic, query):
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory data available."

    # Filter by topic
    entries = [entry for entry in data if entry.get("topic", "").lower() == topic.lower()]
    if not entries:
        return f"No entries found for topic '{topic}'."

    # Rank and summarize
    ranked_texts = [entry["response"] for entry in entries if "response" in entry]
    summary = summarize_ranked_results(ranked_texts, query)

    # Log summary
    save_memory_entry(
        user_input=f"summary for {topic}",
        response=summary,
        tone="summary",
        topic=topic
    )

    return f"Logged summary for '{topic}': {summary}"

def launch_phase10_11():
    with gr.Blocks() as app:
        gr.Markdown("### SoulNode | Phase 10.11 – Ranked Summary & Logging")

        with gr.Row():
            topic = gr.Textbox(label="Memory Topic (e.g. motivation, glucose, dadmode)")
            query = gr.Textbox(label="Custom Query (optional for refining summary)")

        result = gr.Textbox(label="Summary Output")

        run_btn = gr.Button("Summarize & Log")
        run_btn.click(fn=summarize_and_log, inputs=[topic, query], outputs=result)

    app.launch()

if __name__ == "__main__":
    launch_phase10_11()