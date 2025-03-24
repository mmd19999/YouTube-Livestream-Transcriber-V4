"""
Major topic detection module for YouTube Livestream Transcriber.
Analyzes transcription chunks to detect significant topic changes for YouTube content.
Generates detailed, YouTube-optimized section titles with keywords.
"""

import os
import logging
import threading
import queue
import time
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
topic_start_timestamp = None

# Two-stage context model
previous_topic_transcription = []  # Complete transcription for the previous topic
current_transcription = []  # Current transcription being analyzed

last_topic_change_timestamp = None
min_topic_duration_chunks = 2  # Minimum chunks before allowing topic change
socketio_instance = None  # Store socketio instance for use when stopping

# Memory management - max chunks per topic before summarizing
MAX_CURRENT_CHUNKS = 100  # After this many chunks, start summarizing to save memory
MAX_PREV_SUMMARY_LENGTH = 5000  # Maximum characters for previous topic summary


def start_major_topic_detection(socketio):
    """Start the major topic detection thread"""
    global detection_thread, stop_detection_flag, current_major_topic, previous_major_topic
    global topic_start_timestamp, previous_topic_transcription, current_transcription
    global last_topic_change_timestamp, socketio_instance

    stop_detection_flag = False
    current_major_topic = None
    previous_major_topic = None
    topic_start_timestamp = None
    previous_topic_transcription = []
    current_transcription = []
    last_topic_change_timestamp = None
    socketio_instance = socketio  # Store for later use

    detection_thread = threading.Thread(
        target=major_topic_detection_worker, args=(socketio,)
    )
    detection_thread.daemon = True
    detection_thread.start()
    logger.info("Major topic detection thread started")


def stop_major_topic_detection():
    """Stop the major topic detection thread"""
    global stop_detection_flag, current_major_topic, topic_start_timestamp, current_transcription, socketio_instance

    # Before stopping, emit the final topic if we have one
    if (
        socketio_instance
        and current_major_topic
        and topic_start_timestamp
        and current_transcription
    ):
        try:
            # Get the last timestamp from the current transcription
            last_timestamp = current_transcription[-1]["timestamp"]
            interval = f"{topic_start_timestamp}-{last_timestamp}"

            # Log and emit the completed topic
            log_message = (
                f"Final major topic completed: {current_major_topic} ({interval})"
            )
            logger.info(log_message)

            socketio_instance.emit(
                "debug_log", {"message": log_message, "type": "success"}
            )
            socketio_instance.emit(
                "major_topic_change",
                {"interval": interval, "topic": current_major_topic},
            )
        except Exception as e:
            logger.error(f"Error emitting final topic: {str(e)}")

    stop_detection_flag = True
    logger.info("Major topic detection thread stopping")


def add_transcription_for_major_analysis(timestamp, text):
    """Add a transcription chunk to the major topic analysis queue"""
    global major_topic_queue
    major_topic_queue.put({"timestamp": timestamp, "text": text})
    logger.debug(f"Added transcription to major topic detection queue at {timestamp}")


def major_topic_detection_worker(socketio):
    """Worker thread that processes transcriptions and detects major topic changes"""
    global major_topic_queue, current_major_topic, previous_major_topic, stop_detection_flag
    global topic_start_timestamp, current_transcription, last_topic_change_timestamp

    while not stop_detection_flag:
        try:
            # Get transcription from queue with timeout to allow checking stop flag
            try:
                transcription = major_topic_queue.get(timeout=1.0)
            except queue.Empty:
                # No new transcriptions, just continue
                continue

            timestamp = transcription["timestamp"]
            text = transcription["text"]

            # Process the new transcription
            process_transcription(socketio, timestamp, text)

        except Exception as e:
            error_message = f"Error in major topic detection worker: {str(e)}"
            logger.error(error_message)
            socketio.emit("debug_log", {"message": error_message, "type": "error"})


def manage_memory_usage():
    """Manage memory by summarizing if needed"""
    global current_transcription, previous_topic_transcription

    # If current transcription is too large, keep only the most recent chunks
    if len(current_transcription) > MAX_CURRENT_CHUNKS:
        # Keep the first chunk (for timestamp), most recent chunks, and middle context
        start_chunk = current_transcription[0]
        recent_chunks = current_transcription[-50:]  # Keep the 50 most recent chunks

        # Log memory management
        logger.info(
            f"Memory management: Reducing current transcription from {len(current_transcription)} to 51 chunks"
        )

        # Reset with selected chunks
        current_transcription = [start_chunk] + recent_chunks

    # Ensure previous topic transcription doesn't get too large
    if previous_topic_transcription:
        combined_text = " ".join(
            [item["text"] for item in previous_topic_transcription]
        )
        if len(combined_text) > MAX_PREV_SUMMARY_LENGTH:
            # Keep only start and end timestamps but summarize text
            first_chunk = previous_topic_transcription[0]
            last_chunk = previous_topic_transcription[-1]

            # Create a summarized version (keeping important timestamps)
            previous_topic_transcription = [
                first_chunk,
                {
                    "timestamp": "summary",
                    "text": combined_text[:MAX_PREV_SUMMARY_LENGTH],
                },
                last_chunk,
            ]
            logger.info("Memory management: Summarized previous topic transcription")


def process_transcription(socketio, timestamp, text):
    """Process a single transcription chunk for major topic detection"""
    global current_major_topic, previous_major_topic, topic_start_timestamp
    global current_transcription, previous_topic_transcription, last_topic_change_timestamp

    # Add to current transcription collection
    current_transcription.append({"timestamp": timestamp, "text": text})

    # Manage memory if needed
    manage_memory_usage()

    # Skip if we just had a topic change (enforce minimum topic duration)
    chunks_since_last_change = 0
    if last_topic_change_timestamp:
        for item in current_transcription:
            if item["timestamp"] > last_topic_change_timestamp:
                chunks_since_last_change += 1

        if chunks_since_last_change < min_topic_duration_chunks:
            logger.debug(
                f"Skipping topic analysis (minimum duration not met): {chunks_since_last_change} chunks since last change"
            )
            return

    # Log analysis start
    log_message = f"Analyzing for major topic change at {timestamp}"
    logger.info(log_message)
    socketio.emit("debug_log", {"message": log_message})

    try:
        # Combine current transcription for analysis
        combined_text = " ".join([item["text"] for item in current_transcription])

        # Get previous topic context if available
        prev_context = ""
        if previous_topic_transcription:
            # Get text from previous topic (limit length to avoid token issues)
            prev_text = " ".join(
                [item["text"] for item in previous_topic_transcription]
            )
            if len(prev_text) > 1000:  # Limit context length
                prev_context = prev_text[:1000] + "..."
            else:
                prev_context = prev_text

        # Detect if there's a topic change
        new_topic, is_topic_change, confidence = detect_major_topic_change(
            combined_text, current_major_topic, prev_context
        )

        if current_major_topic is None:
            # This is the first topic - store it, don't emit yet
            current_major_topic = new_topic
            topic_start_timestamp = timestamp
            last_topic_change_timestamp = timestamp

            # Log detection
            log_message = f"Initial major topic detected: {new_topic}"
            logger.info(log_message)
            socketio.emit("debug_log", {"message": log_message, "type": "success"})

        elif (
            is_topic_change and confidence >= 0.65
        ):  # Lower threshold to catch more meaningful transitions
            # Topic has changed - now we can emit the previous topic
            interval = f"{topic_start_timestamp}-{timestamp}"

            # Log and emit the completed topic
            log_message = f"Major topic completed: {current_major_topic} ({interval})"
            logger.info(log_message)
            socketio.emit("debug_log", {"message": log_message, "type": "success"})
            socketio.emit(
                "major_topic_change",
                {"interval": interval, "topic": current_major_topic},
            )

            # Move current context to previous context
            previous_major_topic = current_major_topic
            previous_topic_transcription = current_transcription.copy()

            # Update to the new topic and reset current transcription
            current_major_topic = new_topic
            current_transcription = [
                {"timestamp": timestamp, "text": text}
            ]  # Keep the current chunk
            topic_start_timestamp = timestamp
            last_topic_change_timestamp = timestamp

            # Log topic change
            log_message = f"New major topic detected: {new_topic}"
            logger.info(log_message)
            socketio.emit("debug_log", {"message": log_message, "type": "success"})
        else:
            # No topic change
            log_message = (
                f"No major topic change detected (confidence: {confidence:.2f})"
            )
            logger.debug(log_message)

    except Exception as e:
        error_message = f"Major topic detection failed: {str(e)}"
        logger.error(error_message)
        socketio.emit("debug_log", {"message": error_message, "type": "error"})


def call_openai_with_retry(
    messages, model="gpt-4o-mini-2024-07-18", max_tokens=150, retries=2
):
    """Call OpenAI API with retry logic"""
    for attempt in range(retries + 1):
        try:
            return openai.ChatCompletion.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                timeout=30,  # Add timeout
            )
        except Exception as e:
            if attempt < retries:
                logger.warning(
                    f"OpenAI API call failed (attempt {attempt+1}/{retries+1}): {str(e)}"
                )
                time.sleep(2)  # Wait before retry
                continue
            else:
                # Final attempt failed
                logger.error(
                    f"OpenAI API call failed after {retries+1} attempts: {str(e)}"
                )
                raise


def detect_major_topic_change(current_text, previous_topic, previous_context=""):
    """Use GPT-4o mini to detect significant topic changes and generate detailed topics"""

    # First topic case
    if previous_topic is None:
        # For the first topic, we just determine what it is
        prompt = f"""You are analyzing a segment of transcription from a crypto YouTube livestream.
        
Transcription: "{current_text}"

Generate a detailed, engaging YouTube-style chapter title that captures the major topic being discussed.
Include specific crypto assets, technical indicators, or market conditions mentioned in the discussion.
Your title should follow the format "Main Topic - Specific Detail" and be concise yet specific.

Return your response in this exact format:
[Major Topic: <detailed title>]"""

        # Call OpenAI API with retry
        try:
            response = call_openai_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert crypto content creator specializing in YouTube chapter markers for cryptocurrency livestreams. Your task is to analyze livestream transcriptions and create perfect YouTube chapter titles.

Guidelines:
• Create titles that follow the format "Main Topic - Specific Detail" (e.g., "Bitcoin Analysis - Bull Flag Formation")
• Always include specific cryptocurrency assets by ticker (BTC, ETH, SOL, ADA, DOGE, etc.) when relevant
• Include technical indicators, chart patterns, or news events (RSI, FOMC, Breakout, Support Levels, etc.)
• Keep titles concise yet specific (5-15 words is ideal)
• Use crypto-specific terminology appropriate for traders (Short Squeeze, Liquidation, Accumulation, etc.)
• When appropriate, use a question format to create engagement ("Is Bitcoin Ready to Pump?")
• Capture exactly what's being discussed - focus on the main point, not tangential details

Examples directly from successful crypto videos:
- "Bitcoin Analysis - Hope Stage"
- "Crypto Total Market Cap Analysis - RSI Flatline"
- "Altcoins Parabolic Moves Incoming"
- "Bitcoin Scenarios - BTC"
- "Crypto Pullback Post Bybit Hack - Intro"
- "High Liquidation Event"
- "Will Arweave Explode This Year?"
- "Bitcoin Short Squeeze Imminent - BTC Analysis"
- "CPI Forecast Today - Good For Crypto?"
- "Eric Trump Crypto KOL? - BTC Tweet"

Always return just the title in this format: [Major Topic: <detailed title>]""",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
            )

            topic_text = response.choices[0].message.content.strip()

            # Extract topic from response format [Major Topic: <topic>]
            if "[Major Topic:" in topic_text and "]" in topic_text:
                topic = topic_text.split("[Major Topic:")[1].split("]")[0].strip()
            else:
                topic = topic_text

            return topic, True, 1.0  # For first topic, always return high confidence

        except Exception as e:
            logger.error(f"Error determining initial topic: {str(e)}")
            return "Initial Topic", True, 1.0  # Fallback if API fails

    else:
        # For subsequent chunks, determine if there's a significant topic change
        # Include previous context in the prompt if available
        context_info = ""
        if previous_context:
            # Limit context length to avoid token issues
            context_info = f'\nPrevious topic context: "{previous_context[:500]}..."'

        prompt = f"""You are analyzing a segment of transcription from a crypto YouTube livestream.

Current major topic: "{previous_topic}"{context_info}

New transcription segment: "{current_text}"

Your task is to:
1) Determine if this represents a SIGNIFICANT shift to a new topic deserving of a YouTube chapter marker
2) If yes, create a concise, specific title for this new chapter
3) Provide a confidence score (0.0-1.0) on how certain you are that this is a major topic change

Consider:
- A YouTube chapter-worthy change means the conversation has moved to a distinctly different subject
- Major topic changes often include explicit transitions or shifts to new crypto assets/concepts
- The new title should follow the format "Main Topic - Specific Detail" and be 3-10 words
- Include crypto assets by ticker (BTC, ETH, SOL, etc.) and relevant indicators/events when mentioned

Return your response in this exact format:
[Topic Change: Yes/No]
[Confidence: 0.0-1.0]
[New Major Topic: <detailed title>]"""

        # Call OpenAI API with retry
        try:
            response = call_openai_with_retry(
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert crypto content creator specializing in YouTube chapter markers. Your job is to detect significant topic changes in crypto livestreams and create perfect chapter titles.

Guidelines for topic change detection:
• Be selective - only mark MAJOR shifts in conversation (from one distinct subject to another)
• New chapter markers typically appear every 2-5 minutes in good crypto content
• Look for explicit transitions like "now let's look at..." or "moving on to..."
• A shift from one cryptocurrency to another often indicates a chapter-worthy change
• A shift from market analysis to news discussion is typically a chapter-worthy change
• Changing from general market overview to specific asset analysis is usually a chapter change

Confidence scoring:
• 0.9-1.0: Definite major topic change (explicit transition, completely new subject)
• 0.75-0.89: Strong topic change (clear shift to new crypto asset or concept)
• 0.5-0.74: Moderate topic change (related but distinct subject)
• 0.0-0.49: Minor variation or continuation of same general topic (not chapter-worthy)

Title creation guidelines:
• Create titles that follow the format "Main Topic - Specific Detail" 
• Always include specific crypto assets (BTC, ETH, SOL, ADA, DOGE, etc.) when relevant
• Include technical indicators or news events (RSI, FOMC, Breakout, Support Levels)
• Keep titles concise yet specific (5-15 words is ideal)
• Use crypto-specific terminology (Short Squeeze, Liquidation, Accumulation, etc.)
• Question formats can create engagement ("Is Bitcoin Ready to Pump?")

Examples directly from successful crypto videos:
- "Bitcoin Analysis - Hope Stage"
- "Altcoins Parabolic Moves Incoming"
- "What Stage is Crypto in Today? - Crypto Emotions"
- "Bitcoin Relief Rally? - Crypto Market Update"
- "News Following to Jerome Powell FOMC Meeting"
- "Crypto Total Market Cap Analysis - TOTAL"
- "What Do Trumps Tariffs Mean For Crypto?"
- "FOMC Meeting Today - Intro"
- "How To Trade Crypto When The Market Turns?"
- "Bitcoin Short Squeeze Imminent - BTC Analysis"

Return your response in this exact format without additional commentary:
[Topic Change: Yes/No]
[Confidence: 0.0-1.0]
[New Major Topic: <detailed title>]""",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=150,
            )

            response_text = response.choices[0].message.content.strip()

            # Parse the response
            is_topic_change = False
            confidence = 0.0
            new_topic = previous_topic  # Default to keeping the same topic

            if "[Topic Change:" in response_text:
                change_part = (
                    response_text.split("[Topic Change:")[1].split("]")[0].strip()
                )
                is_topic_change = change_part.lower() == "yes"

            if "[Confidence:" in response_text:
                confidence_part = (
                    response_text.split("[Confidence:")[1].split("]")[0].strip()
                )
                try:
                    confidence = float(confidence_part)
                except ValueError:
                    # If we can't parse confidence, default to 0.5
                    confidence = 0.5

            if "[New Major Topic:" in response_text:
                new_topic_part = (
                    response_text.split("[New Major Topic:")[1].split("]")[0].strip()
                )
                if new_topic_part.strip():  # Only update if we got a non-empty topic
                    new_topic = new_topic_part

            return new_topic, is_topic_change, confidence

        except Exception as e:
            logger.error(f"Error detecting topic change: {str(e)}")
            return previous_topic, False, 0.0  # Fallback if API fails
