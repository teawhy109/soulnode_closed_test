import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_gpt_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an emotionally intelligent AI assistant named Solenoid."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500,
            n=1,
            stop=None
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"An error occurred: {str(e)}"