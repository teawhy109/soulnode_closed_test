def generate_ai_response(message, mode="neutral"):
    message = message.strip().lower()

    if mode == "soulful":
        return f"Here's a soulful reflection: '{message.capitalize()}.' What you’re touching on holds weight — and heart."
    
    elif mode == "tactical":
        return f"EXECUTE: '{message.capitalize()}'. Here's the strategy — fast, sharp, clean."

    elif mode == "humorous":
        return f"You really said: '{message.capitalize()}'. That’s almost as wild as SoNo trying to use a spatula as a mic."

    elif mode == "affirming":
        return f"Powerful words: '{message.capitalize()}'. You’re showing up and that matters — don’t forget it."

    elif mode == "neutral":
        return f"You said: '{message.capitalize()}'. Noted and processed."

    else:
        return f"(Unknown mode: {mode}). Here's your message: '{message.capitalize()}'."