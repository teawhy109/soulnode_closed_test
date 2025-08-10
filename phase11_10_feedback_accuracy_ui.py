import gradio as gr
import json

def load_feedback_audit():
    try:
        with open("Tone_Feedback_Audit.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def display_audit_summary():
    audit_log = load_feedback_audit()
    total = len(audit_log)
    correct = sum(1 for entry in audit_log if entry["status"] == "correct")
    incorrect = sum(1 for entry in audit_log if entry["status"] == "incorrect")
    summary = f"Total: {total} |  Correct: {correct} |  Incorrect: {incorrect}"
    return summary, audit_log

def launch_phase11_10():
    with gr.Blocks() as app:
        gr.Markdown("### Phase 11.10 – Feedback Accuracy Dashboard")

        summary_text = gr.Textbox(label="Summary")
        full_log = gr.Dataframe(headers=["Input", "Predicted", "Correct", "Status"], label="Audit Log")

        run_btn = gr.Button("Load Audit Results")
        run_btn.click(
            fn=lambda: (
                display_audit_summary()[0],
                [[e["input"], e["predicted"], e["correct"], e["status"]] for e in display_audit_summary()[1]]
            ),
            outputs=[summary_text, full_log]
        )

    app.launch()

if __name__ == "__main__":
    launch_phase11_10()