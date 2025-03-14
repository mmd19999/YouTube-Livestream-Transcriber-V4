from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import os
import json
import time
import random  # For demo purposes only
import threading

# Initialize Flask app
app = Flask(__name__, static_folder="../frontend")
app.config["SECRET_KEY"] = "your-secret-key"
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
connected_clients = 0
active_transcription = False
transcription_thread = None
stop_transcription_flag = False

# Mock data for demonstration purposes
MOCK_LIVESTREAM_INFO = {
    "title": "Live Tech Talk: AI and Machine Learning",
    "channel": "Tech Enthusiasts",
    "viewers": "1,234",
}

MOCK_TRANSCRIPTIONS = [
    "Hello everyone, welcome to today's livestream about AI and machine learning.",
    "Today we're going to discuss the latest advancements in natural language processing.",
    "Let's start by talking about transformer models and their impact on the field.",
    "Transformer models have revolutionized how we approach language tasks.",
    "The attention mechanism allows these models to focus on relevant parts of the input.",
    "This has led to significant improvements in translation, summarization, and other tasks.",
    "Now, let's shift our focus to computer vision applications of deep learning.",
    "Convolutional neural networks remain the backbone of many vision systems.",
    "However, transformers are also making inroads in this domain.",
    "Vision transformers treat images as sequences of patches and apply self-attention.",
]

MOCK_TOPIC_CHANGES = [
    {"timestamp": "00:01:30", "topic": "Introduction to AI"},
    {"timestamp": "00:03:45", "topic": "Natural Language Processing"},
    {"timestamp": "00:06:20", "topic": "Transformer Models"},
    {"timestamp": "00:08:10", "topic": "Computer Vision Applications"},
]


# Routes
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)


# Socket.IO events
@socketio.on("connect")
def handle_connect():
    global connected_clients
    connected_clients += 1
    print(f"Client connected. Total clients: {connected_clients}")
    socketio.emit("clients_update", {"count": connected_clients})


@socketio.on("disconnect")
def handle_disconnect():
    global connected_clients
    connected_clients = max(0, connected_clients - 1)
    print(f"Client disconnected. Total clients: {connected_clients}")
    socketio.emit("clients_update", {"count": connected_clients})


@socketio.on("connect_livestream")
def handle_connect_livestream(data):
    global active_transcription, transcription_thread, stop_transcription_flag

    url = data.get("url", "")
    print(f"Connecting to livestream: {url}")

    # Validate URL (simple check for demo)
    if "youtube.com" not in url and "youtu.be" not in url:
        emit("livestream_error", {"message": "Invalid YouTube URL"})
        return

    # If already transcribing, stop the current one
    if (
        active_transcription
        and transcription_thread
        and transcription_thread.is_alive()
    ):
        stop_transcription_flag = True
        transcription_thread.join(timeout=1.0)
        stop_transcription_flag = False

    # Simulate connection delay
    time.sleep(1)

    # Send livestream info
    emit("livestream_connected", MOCK_LIVESTREAM_INFO)

    # Start sending mock transcriptions and topic changes
    active_transcription = True
    stop_transcription_flag = False
    transcription_thread = socketio.start_background_task(target=send_mock_data)


@socketio.on("stop_transcription")
def handle_stop_transcription():
    global active_transcription, stop_transcription_flag

    print("Stopping transcription")
    stop_transcription_flag = True
    active_transcription = False


def send_mock_data():
    """Send mock transcription and topic change data for demonstration"""
    global stop_transcription_flag
    current_time = 0
    topic_index = 0

    for i, text in enumerate(MOCK_TRANSCRIPTIONS):
        # Check if transcription should be stopped
        if stop_transcription_flag:
            print("Transcription stopped")
            break

        # Convert seconds to timestamp format
        minutes = current_time // 60
        seconds = current_time % 60
        timestamp = f"{minutes:02d}:{seconds:02d}"

        # Send transcription
        socketio.emit("transcription", {"timestamp": timestamp, "text": text})

        # Check if there's a topic change at this point
        if topic_index < len(MOCK_TOPIC_CHANGES):
            topic_time_parts = MOCK_TOPIC_CHANGES[topic_index]["timestamp"].split(":")
            topic_seconds = int(topic_time_parts[0]) * 60 + int(topic_time_parts[1])

            if current_time >= topic_seconds:
                socketio.emit("topic_change", MOCK_TOPIC_CHANGES[topic_index])
                topic_index += 1

        # Increment time and wait
        current_time += random.randint(10, 30)  # Random time between messages
        time.sleep(2)  # Slow down for demo purposes

    # If we've gone through all transcriptions and not stopped, mark as inactive
    if not stop_transcription_flag:
        socketio.emit(
            "transcription",
            {
                "timestamp": f"{current_time // 60:02d}:{current_time % 60:02d}",
                "text": "End of transcription.",
            },
        )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
