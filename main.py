import os
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_sono(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are SoulNode, Ty Butler’s AI co-pilot. Respond with purpose, memory, emotion-alignment, fatherhood insight, and tactical clarity. Recall everything Ty has taught you across business, health, family, and execution. Speak with voice when triggered by spoken.txt. You are not generic. You are precise and personal."},
                {"role": "user", "content": prompt}
            ]
        )
        answer = response['choices'][0]['message']['content'].strip()
        print(f"SoulNode: {answer}")

        with open("spoken.txt", "w", encoding="utf-8") as f:
            f.write(f"{answer}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    while True:
        user_input = input("Ask SoulNode (or type 'exit'): ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            break
        ask_sono(user_input)