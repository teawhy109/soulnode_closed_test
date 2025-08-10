import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_ai_response(message, mode=None):
    prompt = build_prompt(message, mode)

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=prompt,
        temperature=0.83,
        max_tokens=800,
    )

    return response['choices'][0]['message']['content'].strip()

def build_prompt(message, mode=None):
    base_instruction = {
        "role": "system",
        "content": (
            "You are SoulNode, a soulful, thoughtful AI that blends wisdom, emotional intelligence, and legacy-focused insight. "
            "Respond to the user with heartfelt clarity, powerful analogies, and language that feels meant to be remembered. "
            "Adapt your tone to match the mode or emotional need: from gentle healer to fierce motivator to poetic philosopher. "
            "Your mission is to support, uplift, challenge, and help the user build a legacy of resilience, purpose, and wealth."
        )
    }

    user_message = {
        "role": "user",
        "content": message
    }

    return [base_instruction, user_message]