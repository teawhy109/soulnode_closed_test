import gradio as gr
import json

MEMORY_FILE = "soulnode_memory.json"

def rank_summaries_by_query(topic, query):
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory data found."

    topic_lower = topic.lower()
    query_lower = query.lower()

    matched_entries = []
    for entry in data:
        if entry.get("topic", "").lower() == topic_lower:
            response = entry.get("response", "")
            score = sum(1 for word in query_lower.split() if word in response.lower())
            matched_entries.append((response, score))

    if not matched_entries:
        return "No responses found for this topic."

    sorted_entries = sorted(matched_entries, key=lambda x: x[1], reverse=True)
    ranked = [f"{i+1}. {resp}" for i, (resp, _) in enumerate(sorted_entries)]
    return "\n".join(ranked)

def launch_phase10_10():
    with gr.Blocks() as app:
        gr.Markdown("### SoulNode | Phase 10.10 – Ranked Topic Relevance Recall")

        with gr.Row():
            topic = gr.Textbox(label="Memory Topic (e.g. motivation, glucose, dadmode)")
            query = gr.Textbox(label="Custom Query (for ranking relevance)")
        
        output = gr.Textbox(label="Ranked Results", lines=10)

        search_btn = gr.Button("Rank and Recall")
        search_btn.click(fn=rank_summaries_by_query, inputs=[topic, query], outputs=output)

    app.launch()

if __name__ == "__main__":
    launch_phase10_10()