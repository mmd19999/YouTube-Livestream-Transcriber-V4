"""
Major topic detection module for YouTube Livestream Transcriber.
Analyzes transcription chunks in 5-minute intervals to detect broader topics.
Runs alongside the existing fine-grained topic detection.
"""

import os
import logging
import threading
import time
import queue
import openai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables and set up OpenAI API key
load_dotenv()
# First check if a temporary API key is set, otherwise use the one from .env
openai.api_key = os.environ.get("TEMP_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

# Global variables
major_topic_queue = queue.Queue()
current_major_topic = None
previous_major_topic = None
stop_detection_flag = False
detection_thread = None
batch_start_time = None
current_batch_transcriptions = []

# Constants
BATCH_INTERVAL_SECONDS = 300  # 5 minutes


def start_major_topic_detection(socketio):
    """Start the major topic detection thread"""
    global detection_thread, stop_detection_flag, batch_start_time, current_batch_transcriptions

    stop_detection_flag = False
    batch_start_time = time.time()
    current_batch_transcriptions = []

    detection_thread = threading.Thread(
        target=major_topic_detection_worker, args=(socketio,)
    )
    detection_thread.daemon = True
    detection_thread.start()
    logger.info("Major topic detection thread started")


def stop_major_topic_detection():
    """Stop the major topic detection thread"""
    global stop_detection_flag

    stop_detection_flag = True
    logger.info("Major topic detection thread stopping")


def add_transcription_for_major_analysis(timestamp, text):
    """Add a transcription chunk to the major topic analysis queue"""
    global major_topic_queue

    major_topic_queue.put({"timestamp": timestamp, "text": text})
    logger.debug(f"Added transcription to major topic detection queue at {timestamp}")


def format_interval_timestamp(start_seconds, end_seconds):
    """Format a time interval as HH:MM:SS-HH:MM:SS"""
    start_hours, remainder = divmod(int(start_seconds), 3600)
    start_minutes, start_seconds = divmod(remainder, 60)

    end_hours, remainder = divmod(int(end_seconds), 3600)
    end_minutes, end_seconds = divmod(remainder, 60)

    return f"{start_hours:02d}:{start_minutes:02d}:{start_seconds:02d}-{end_hours:02d}:{end_minutes:02d}:{end_seconds:02d}"


def major_topic_detection_worker(socketio):
    """Worker thread that processes transcriptions in 5-minute batches and detects major topics"""
    global major_topic_queue, current_major_topic, previous_major_topic, stop_detection_flag
    global batch_start_time, current_batch_transcriptions

    batch_end_time = batch_start_time + BATCH_INTERVAL_SECONDS

    while not stop_detection_flag:
        try:
            # Check if it's time to process the current batch
            current_time = time.time()

            if current_time >= batch_end_time:
                # Time to process the batch
                process_current_batch(socketio, batch_start_time, batch_end_time)

                # Set up for next batch
                previous_major_topic = current_major_topic
                batch_start_time = batch_end_time
                batch_end_time = batch_start_time + BATCH_INTERVAL_SECONDS
                current_batch_transcriptions = []

            # Get transcription from queue with timeout to allow checking stop flag
            try:
                transcription = major_topic_queue.get(timeout=1.0)
                current_batch_transcriptions.append(transcription)
                logger.debug(
                    f"Added transcription to current batch: {transcription['timestamp']}"
                )
            except queue.Empty:
                # No new transcriptions, just continue
                continue

        except Exception as e:
            error_message = f"Error in major topic detection worker: {str(e)}"
            logger.error(error_message)
            socketio.emit("debug_log", {"message": error_message, "type": "error"})
            time.sleep(1)  # Avoid tight loop in case of persistent errors


def process_current_batch(socketio, start_time, end_time):
    """Process the current batch of transcriptions to generate a major topic"""
    global current_batch_transcriptions, current_major_topic, previous_major_topic

    if not current_batch_transcriptions:
        logger.info("No transcriptions in current batch to process")
        return

    # Combine all transcriptions into a single text
    combined_text = " ".join([item["text"] for item in current_batch_transcriptions])

    if not combined_text.strip():
        logger.info("Empty combined text, skipping major topic detection")
        return

    # Create time interval string - use elapsed seconds from batch start and end
    elapsed_start = 0  # First batch starts at 0
    elapsed_end = int(end_time - start_time)

    # If we have timestamps from transcriptions, use them instead
    if current_batch_transcriptions:
        # Try to get the first and last timestamps for more accurate representation
        try:
            # Some transcripts might be missing timestamps, so use the ones that have them
            timestamps = [
                t["timestamp"] for t in current_batch_transcriptions if "timestamp" in t
            ]
            if timestamps:
                interval = f"{timestamps[0]}-{timestamps[-1]}"
            else:
                interval = format_interval_timestamp(elapsed_start, elapsed_end)
        except Exception:
            # Fall back to calculated timestamps if anything goes wrong
            interval = format_interval_timestamp(elapsed_start, elapsed_end)
    else:
        interval = format_interval_timestamp(elapsed_start, elapsed_end)

    # Log analysis start
    log_message = f"Analyzing 5-minute batch for major topic detection ({interval})"
    logger.info(log_message)
    socketio.emit("debug_log", {"message": log_message})

    try:
        # Detect the major topic
        major_topic = detect_major_topic(combined_text, previous_major_topic)

        # Update current major topic
        current_major_topic = major_topic

        # Log the new major topic
        log_message = f"Major topic detected: {major_topic} for interval {interval}"
        logger.info(log_message)
        socketio.emit("debug_log", {"message": log_message, "type": "success"})

        # Send major topic change to frontend
        socketio.emit(
            "major_topic_change", {"interval": interval, "topic": major_topic}
        )

    except Exception as e:
        error_message = f"Major topic detection failed: {str(e)}"
        logger.error(error_message)
        socketio.emit("debug_log", {"message": error_message, "type": "error"})


def detect_major_topic(current_batch_text, previous_topic):
    """Use GPT-4o mini to detect major topics for 5-minute intervals"""

    # Prepare the prompt for the LLM
    if previous_topic is None:
        # First 5-minute batch - determine the initial major topic
        prompt = f"""You are analyzing a 5-minute segment of transcription from a YouTube livestream.
        
Transcription: "{current_batch_text}"

Identify a broad, general topic that covers this entire 5-minute segment.
Return your response in this exact format - just the topic name, no explanations:
[Major Topic: <brief topic name>]"""

    else:
        # Subsequent batch - consider previous major topic for context
        prompt = f"""You are analyzing a 5-minute segment of transcription from a YouTube livestream.

Previous 5-minute segment had this major topic: "{previous_topic}"

Current 5-minute transcription: "{current_batch_text}"

Identify a broad, general topic that covers this new 5-minute segment, considering how it evolved from the previous topic.
Return your response in this exact format - just the topic name, no explanations:
[Major Topic: <brief topic name>]"""

    # Call OpenAI API
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini-2024-07-18",
        messages=[
            {
                "role": "system",
                "content": "You identify broad topics covering 5-minute segments of content. Be concise.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=50,
    )

    topic_text = response.choices[0].message.content.strip()

    # Extract topic from response format [Major Topic: <topic>]
    if "[Major Topic:" in topic_text and "]" in topic_text:
        topic = topic_text.split("[Major Topic:")[1].split("]")[0].strip()
    else:
        topic = topic_text

    return topic
