import gradio as gr
from logic import promote_to_map

from brains.response_map import response_map
from brains.health_tracking import health_map
from brains.credit_ops import credit_map
from brains.content_strategy import content_map
from brains.mental_reset import mental_map
from brains.business_build import business_map
from brains.content_growth import growth_map

# Map dropdown labels to actual brain dictionaries
brain_map_dict = {
    "health_tracking": health_map,
    "credit_ops": credit_map,
    "content_strategy": content_map,
    "mental_reset": mental_map,
    "business_build": business_map,
    "content_growth": content_map,
    "response_map": response_map
}

def handle_promote(selected_map, promote_input, desired_response):
    result = promote_to_map(brain_map_dict.get(selected_map, {}), promote_input, desired_response)
    return result

def launch_phase84():
    with gr.Blocks(title="SoulNode | Phase 8.4 | Promote Intelligence") as app:
        gr.Markdown("### Promote Unknown Input to Intelligence")

        promote_input = gr.Textbox(label="Unknown Input to Promote")
        selected_map = gr.Dropdown(
            choices=list(brain_map_dict.keys()),
            label="Select Brain Map"
        )
        desired_response = gr.Textbox(label="Desired Response")
        promote_output = gr.Textbox(label="Result")

        promote_btn = gr.Button("Promote")
        promote_btn.click(
            fn=handle_promote,
            inputs=[selected_map, promote_input, desired_response],
            outputs=promote_output
        )

    app.launch()

if __name__ == "__main__":
    launch_phase84()