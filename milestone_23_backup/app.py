from flask import Flask, request, jsonify
from soulnode_memory import SoulNodeMemory
from soul_core import generate_ai_response

app = Flask(__name__)
memory = SoulNodeMemory()

@app.route("/")
def index():
    return "SoulNode is live."

@app.route("/respond", methods=["POST"])
def respond():
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "Missing 'message' in request body"}), 400

        message = data["message"]
        mode = data.get("mode", "neutral") # default to "neutral" if mode is missing

        response = generate_ai_response(message, mode)
        memory.save(message, response)

        return jsonify({"response": response}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("soulnode_memory.py was successfully loaded")
    app.run(debug=True)