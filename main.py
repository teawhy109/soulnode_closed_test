import gradio as gr
from logic import generate_response # Removed promote_to_map for now

def handle_generate(user_input, user_profile):
    result = generate_response(user_input, user_profile=user_profile)
    return result["response"]

with gr.Blocks() as app:
    gr.Markdown("# SoulNode | Tactical AI Interface")

    with gr.Row():
        user_input = gr.Textbox(label="Your Command")
        user_profile = gr.Textbox(label="User Profile", value="ty")

    output = gr.Textbox(label="SoulNode Response")

    submit_btn = gr.Button("Submit")
    submit_btn.click(
        fn=handle_generate,
        inputs=[user_input, user_profile],
        outputs=output
    )

    gr.Markdown("---")

    selected_map = gr.Dropdown(choices=[
        "health_tracking", "credit_ops", "content_strategy",
        "content_growth", "mental_reset", "business_build"
    ], label="Select Brain Map")

    promote_input = gr.Textbox(label="Unknown Input to Promote")
    desired_response = gr.Textbox(label="Desired Response")

    promote_btn = gr.Button("Promote")
    promote_btn.click(
        fn=None, # Placeholder until promote_to_map is created
        inputs=[selected_map, promote_input, desired_response],
        outputs=output
    )

app.launch()