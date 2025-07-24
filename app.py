from flask import Flask, request, jsonify
from flask_cors import CORS
from memory import SoulNodeMemory

app = Flask(__name__)
CORS(app)

memory = SoulNodeMemory()

@app.route("/save", methods=["POST"])
def save_memory():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        memory.save_memory(data)
        return jsonify({"message": "Memory saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/clear", methods=["POST"])
def clear_memory():
    try:
        memory.clear_memory()
        return jsonify({"message": "Memory cleared successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/export", methods=["GET"])
def export_memory():
    try:
        result = memory.export_memory()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)

    import os

app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))