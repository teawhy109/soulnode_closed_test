from flask import Flask, request, jsonify
from memory import SoulNodeMemory
import os

app = Flask(__name__)
memory = SoulNodeMemory()

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "SoulNode is active"}), 200

@app.route("/remember", methods=["POST"])
def remember():
    data = request.json
    key = data.get("key")
    value = data.get("value")
    if key and value:
        memory.remember(key, value)
        return jsonify({"message": "Memory stored"}), 200
    return jsonify({"error": "Missing key or value"}), 400

@app.route("/recall/<key>", methods=["GET"])
def recall(key):
    value = memory.recall(key)
    if value:
        return jsonify({"value": value}), 200
    return jsonify({"error": "Key not found"}), 404

@app.route("/export", methods=["GET"])
def export_memory():
    try:
        result = memory.export_memory()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))