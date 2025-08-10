import gradio as gr
import json

MEMORY_FILE = "spoken_memory.json"

def flag_memory(original_phrase, updated_phrase, reason):
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return "Error loading memory file."
    
    for entry in data:
        if entry["input"].lower() == original_phrase.lower():
            entry["input"] = updated_phrase
            entry["override_reason"] = reason
            entry["override_flagged"] = True
            break
    else:
        return "Original phrase not found."

    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

    return f"✅ Memory updated. New phrase: '{updated_phrase}' | Reason: {reason}"

def launch_phase9_6():
    with gr.Blocks(title=" SoulNode | Phase 9.6 | Flag & Override System") as app:
        gr.Markdown("### Flag and Replace a Spoken Memory")

        with gr.Row():
            original_input = gr.Textbox(label="Original Phrase")
            updated_phrase = gr.Textbox(label="Updated Phrase")
            reason = gr.Textbox(label="Reason for Override")

        output = gr.Textbox(label="Override Result")

        submit_btn = gr.Button("Override Now")
        submit_btn.click(fn=flag_memory, inputs=[original_input, updated_phrase, reason], outputs=output)

    app.launch()

if __name__ == "__main__":
    launch_phase9_6()