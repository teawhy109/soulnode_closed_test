def get_response_for_prompt(user_input):
    user_input = user_input.lower()

    if "hello" in user_input:
        return "Hey there! How can I help you today?"

    elif "how are you" in user_input:
        return "I'm operating at full capacity. Thanks for asking!"

    elif "what is your name" in user_input:
        return "I'm SoulNode, your AI co-pilot."

    elif "how far is the moon from earth" in user_input:
        return "The Moon is approximately 238,855 miles or 384,400 kilometers from Earth."

    elif "who created you" in user_input:
        return "I was created by Ty Butler and René as part of the SoulNode project under New Chapter Media Group."

    elif "what can you do" in user_input:
        return "I can answer questions, generate audio, assist with memory, and help you stay locked into your mission."

    else:
        return "I'm still learning that one. Want to try asking it a different way?"