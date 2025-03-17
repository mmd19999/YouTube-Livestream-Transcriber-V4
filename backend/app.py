# Import gevent and monkey patch FIRST - before any other imports
from gevent import monkey

monkey.patch_all()

# Now it's safe to import everything else
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import os
import json
import time
import threading
import logging
from dotenv import load_dotenv
import transcription
import topic_detection  # Add import for topic detection module
import major_topic_detection  # Add import for major topic detection module
import datetime  # Added for timestamp handling

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder="../frontend")
app.config["SECRET_KEY"] = "your-secret-key"
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="gevent",
    logger=True,
    engineio_logger=True,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variabless
connected_clients = 0
active_transcription = False
transcription_thread = None
stop_transcription_flag = False


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
    logger.info(f"Client connected. Total clients: {connected_clients}")
    socketio.emit("clients_update", {"count": connected_clients})
    logger.info(f"Emitted clients_update event with count: {connected_clients}")


@socketio.on("disconnect")
def handle_disconnect():
    global connected_clients
    connected_clients = max(0, connected_clients - 1)
    logger.info(f"Client disconnected. Total clients: {connected_clients}")
    socketio.emit("clients_update", {"count": connected_clients})


@socketio.on("connect_livestream")
def handle_connect_livestream(data):
    global active_transcription, transcription_thread, stop_transcription_flag

    url = data.get("url", "")
    custom_api_key = data.get("apiKey", "")

    log_message = f"Received URL: {url}"
    logger.info(log_message)
    socketio.emit("debug_log", {"message": log_message})

    # Set custom API key if provided
    if custom_api_key:
        log_message = "Using custom API key from frontend"
        logger.info(log_message)
        socketio.emit("debug_log", {"message": log_message})

        # Store the custom API key for later use
        os.environ["TEMP_OPENAI_API_KEY"] = custom_api_key

    # Validate URL (simple check)
    if "youtube.com" not in url and "youtu.be" not in url:
        error_message = "Invalid YouTube URL"
        logger.error(error_message)
        socketio.emit("debug_log", {"message": error_message, "type": "error"})
        socketio.emit("livestream_error", {"message": error_message})
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
        topic_detection.stop_topic_detection()  # Stop the topic detection thread
        major_topic_detection.stop_major_topic_detection()  # Stop the major topic detection thread

    # Start topic detection thread
    topic_detection.start_topic_detection(socketio)
    socketio.emit("debug_log", {"message": "Topic detection thread started"})

    # Start major topic detection thread
    major_topic_detection.start_major_topic_detection(socketio)
    socketio.emit("debug_log", {"message": "Major topic detection thread started"})

    # Start transcription process
    active_transcription = True
    stop_transcription_flag = False
    transcription_thread = socketio.start_background_task(
        target=transcribe_livestream, url=url
    )

    # Send status update
    socketio.emit("livestream_connected", {"status": "connected", "url": url})
    logger.info(f"Emitted livestream_connected event for URL: {url}")


@socketio.on("stop_transcription")
def handle_stop_transcription():
    global active_transcription, stop_transcription_flag

    log_message = "Stopping transcription"
    logger.info(log_message)
    socketio.emit("debug_log", {"message": log_message})

    stop_transcription_flag = True
    active_transcription = False
    topic_detection.stop_topic_detection()  # Stop the topic detection thread
    major_topic_detection.stop_major_topic_detection()  # Stop the major topic detection thread


@socketio.on("ping")
def handle_ping(data):
    logger.info(f"Received ping: {data}")
    socketio.emit("pong", {"message": "Server received ping"})
    logger.info("Emitted pong response")


def transcribe_livestream(url):
    """Main function to transcribe a YouTube livestream"""
    global stop_transcription_flag, active_transcription

    try:
        # Get the direct audio stream URL
        log_message = f"Extracting audio stream URL from: {url}"
        socketio.emit("debug_log", {"message": log_message})

        audio_url, stream_info = transcription.get_audio_stream_url(url)

        # Send livestream info to frontend
        socketio.emit("livestream_info", stream_info)
        socketio.emit(
            "debug_log",
            {"message": "Successfully extracted audio stream URL", "type": "success"},
        )

        if not audio_url:
            error_message = "Failed to get audio stream URL"
            logger.error(error_message)
            socketio.emit("debug_log", {"message": error_message, "type": "error"})
            socketio.emit("livestream_error", {"message": error_message})
            return

        # Initialize timestamp reference point - the moment transcription begins
        transcription_start_time = datetime.datetime.now()
        logger.info(f"Transcription started at: {transcription_start_time}")
        socketio.emit(
            "debug_log",
            {
                "message": f"Transcription started at: {transcription_start_time.strftime('%H:%M:%S')}"
            },
        )

        # Start transcribing chunks sequentially
        current_time = 0  # Still needed for ffmpeg extraction
        chunk_duration = 20  # seconds

        while not stop_transcription_flag:
            try:
                # Extract audio chunk
                log_message = f"Extracting audio chunk at {transcription.format_timestamp(current_time)}"
                socketio.emit("debug_log", {"message": log_message})

                audio_file = transcription.extract_audio_chunk(
                    audio_url, chunk_duration, current_time
                )

                # Transcribe the audio chunk
                log_message = "Transcribing chunk..."
                socketio.emit("debug_log", {"message": log_message})

                transcription_text = transcription.transcribe_audio_chunk(audio_file)

                # Calculate timestamp based on real-world time
                current_real_time = datetime.datetime.now()
                elapsed_seconds = (
                    current_real_time - transcription_start_time
                ).total_seconds()
                timestamp = transcription.format_timestamp(int(elapsed_seconds))

                # Send transcription to frontend
                log_message = f"Transcription sent to frontend: {transcription_text}"
                logger.info(log_message)
                socketio.emit("debug_log", {"message": log_message, "type": "success"})

                # Emit transcription event to all clients
                socketio.emit(
                    "transcription",
                    {"timestamp": timestamp, "text": transcription_text},
                    broadcast=True,
                )
                logger.info(f"Emitted transcription event with timestamp: {timestamp}")

                # Send transcription for topic change detection
                topic_detection.add_transcription_for_analysis(
                    timestamp, transcription_text
                )

                # Send transcription for major topic detection
                major_topic_detection.add_transcription_for_major_analysis(
                    timestamp, transcription_text
                )

                # Move to next chunk (still needed for ffmpeg extraction)
                current_time += chunk_duration

            except Exception as e:
                error_message = f"Error processing chunk: {str(e)}"
                logger.error(error_message)
                socketio.emit("debug_log", {"message": error_message, "type": "error"})
                # Continue to next chunk even if this one fails
                current_time += chunk_duration
                continue

    except Exception as e:
        error_message = f"Transcription error: {str(e)}"
        logger.error(error_message)
        socketio.emit("debug_log", {"message": error_message, "type": "error"})
        socketio.emit("livestream_error", {"message": error_message})
    finally:
        # Clean up and mark as inactive
        if not stop_transcription_flag:
            # Get final timestamp based on real world time
            current_real_time = datetime.datetime.now()
            elapsed_seconds = (
                current_real_time - transcription_start_time
            ).total_seconds()
            final_timestamp = transcription.format_timestamp(int(elapsed_seconds))

            socketio.emit(
                "transcription",
                {
                    "timestamp": final_timestamp,
                    "text": "Transcription ended due to an error.",
                },
                broadcast=True,
            )

        active_transcription = False
        topic_detection.stop_topic_detection()  # Stop the topic detection thread
        major_topic_detection.stop_major_topic_detection()  # Stop the major topic detection thread

        # Remove temporary API key if it was set
        if "TEMP_OPENAI_API_KEY" in os.environ:
            del os.environ["TEMP_OPENAI_API_KEY"]
            logger.info("Removed temporary API key")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
