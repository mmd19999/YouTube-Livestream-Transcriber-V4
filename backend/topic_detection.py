"""
Topic detection module for YouTube Livestream Transcriber.
Analyzes transcription chunks to detect topic changes using OpenAI's GPT-4o mini.
Runs in parallel with the main transcription process.
"""

import os
import logging
import threading
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
topic_queue = queue.Queue()
current_topic = None
stop_detection_flag = False
detection_thread = None


def start_topic_detection(socketio):
    """Start the topic detection thread"""
    global detection_thread, stop_detection_flag

    stop_detection_flag = False
    detection_thread = threading.Thread(target=topic_detection_worker, args=(socketio,))
    detection_thread.daemon = True
    detection_thread.start()
    logger.info("Topic detection thread started")


def stop_topic_detection():
    """Stop the topic detection thread"""
    global stop_detection_flag

    stop_detection_flag = True
    logger.info("Topic detection thread stopping")


def add_transcription_for_analysis(timestamp, text):
    """Add a transcription chunk to the analysis queue"""
    global topic_queue

    topic_queue.put({"timestamp": timestamp, "text": text})
    logger.info(f"Added transcription to topic detection queue at {timestamp}")


def topic_detection_worker(socketio):
    """Worker thread that processes transcriptions and detects topic changes"""
    global topic_queue, current_topic, stop_detection_flag

    while not stop_detection_flag:
        try:
            # Get transcription from queue with timeout to allow checking stop flag
            try:
                transcription = topic_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            timestamp = transcription["timestamp"]
            text = transcription["text"]

            # Log analysis start
            log_message = f"Analyzing transcription for topic change at {timestamp}"
            logger.info(log_message)
            socketio.emit("debug_log", {"message": log_message})

            # Detect if there's a topic change
            try:
                new_topic, is_topic_change = detect_topic_change(text, current_topic)

                if is_topic_change:
                    # Log topic change
                    log_message = f"Topic change detected: {new_topic} at {timestamp}"
                    logger.info(log_message)
                    socketio.emit(
                        "debug_log", {"message": log_message, "type": "success"}
                    )

                    # Update current topic
                    current_topic = new_topic

                    # Send topic change to frontend
                    socketio.emit(
                        "topic_change", {"timestamp": timestamp, "topic": new_topic}
                    )
                else:
                    # Log no topic change
                    log_message = "No topic change detected"
                    logger.info(log_message)
                    socketio.emit("debug_log", {"message": log_message})

                    # If this is the first transcription, set it as the current topic
                    if current_topic is None:
                        current_topic = new_topic
                        socketio.emit(
                            "topic_change", {"timestamp": timestamp, "topic": new_topic}
                        )

            except Exception as e:
                error_message = f"LLM analysis failed: {str(e)}"
                logger.error(error_message)
                socketio.emit("debug_log", {"message": error_message, "type": "error"})

        except Exception as e:
            error_message = f"Error in topic detection worker: {str(e)}"
            logger.error(error_message)
            socketio.emit("debug_log", {"message": error_message, "type": "error"})


def detect_topic_change(current_text, previous_topic):
    """Use GPT-4o mini to detect topic changes"""

    # Prepare the prompt for the LLM
    if previous_topic is None:
        # First transcript - determine the initial topic
        prompt = f"""Analyze this transcript from a crypto YouTube livestream and determine the main topic. 
        
Transcript: "{current_text}"

Return your response in this exact format - just the topic name, no explanations:
[Topic: <brief topic name>]"""

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role": "system",
                    "content": """You are an advanced section title generator for a crypto YouTube livestream. Your task is to identify topics and create concise, specific titles.

Guidelines:
• Create specific titles that precisely identify what's being discussed in crypto trading
• Use crypto trading terminology appropriate to the discussion
• Keep titles concise but descriptive (3-7 words ideal)
• Format consistently with the crypto trading community style
• Do not provide any commentary - return only the title

Example titles:
- Bitcoin Price Action Analysis
- Bear Market Support Levels
- Leverage Trading Strategies
- Margin Call Risk Assessment
- Market Sentiment Overview
- Exchange Volume Analysis
- Trading Psychology Discussion
- Altcoin Technical Analysis
- Crypto News Breakdown
- Risk Management Techniques
- Chart Pattern Recognition
- Bullish Divergence Signals
- Support/Resistance Levels
- Stop Loss Placement Strategy
- Liquidity Zones Identification
- Moving Average Crossover Analysis""",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=50,
        )

        topic_text = response.choices[0].message.content.strip()

        # Extract topic from response format [Topic: <topic>]
        if "[Topic:" in topic_text and "]" in topic_text:
            topic = topic_text.split("[Topic:")[1].split("]")[0].strip()
        else:
            topic = topic_text

        return topic, True  # First topic is always a "change"

    else:
        # Compare with previous topic
        prompt = f"""Analyze this transcript from a crypto YouTube livestream and determine if there has been a topic change.

Previous topic: "{previous_topic}"

Current transcript: "{current_text}"

Note that there may be some overlap between transcripts due to how they're processed.
Return your response in this exact format:
[Topic Change: Yes/No]
[New Topic: <brief topic name>]"""

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini-2024-07-18",
            messages=[
                {
                    "role": "system",
                    "content": """You are an advanced section title generator for a crypto YouTube livestream. Your task is to identify topic changes and create concise, specific titles.

Guidelines:
• Create specific titles that precisely identify what's being discussed in crypto trading
• Use crypto trading terminology appropriate to the discussion
• Keep titles concise but descriptive (3-7 words ideal)
• Format consistently with the crypto trading community style
• Be judicious about topic changes - only signal a new topic when there's a meaningful shift in content
• Only mark as a topic change if the discussion has substantially moved to a new subject
• Do not provide any commentary - return only the structured response

Example titles:
- Bitcoin Price Action Analysis
- Bear Market Support Levels
- Leverage Trading Strategies
- Margin Call Risk Assessment
- Market Sentiment Overview
- Exchange Volume Analysis
- Trading Psychology Discussion
- Altcoin Technical Analysis
- Crypto News Breakdown
- Risk Management Techniques
- Chart Pattern Recognition
- Bullish Divergence Signals
- Support/Resistance Levels
- Stop Loss Placement Strategy
- Liquidity Zones Identification
- Moving Average Crossover Analysis""",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=100,
        )

        result_text = response.choices[0].message.content.strip()

        # Parse the response
        is_topic_change = "Yes" in result_text.split("[Topic Change:")[1].split("]")[0]

        if "[New Topic:" in result_text and "]" in result_text.split("[New Topic:")[1]:
            new_topic = result_text.split("[New Topic:")[1].split("]")[0].strip()
        else:
            new_topic = previous_topic

        return new_topic, is_topic_change
