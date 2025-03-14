"""
Transcription module for YouTube Livestream Transcriber.
Handles extracting audio from YouTube livestreams and transcribing it using OpenAI's Whisper API.
"""

import os
import tempfile
import subprocess
import datetime
import logging
import yt_dlp
import openai
import multiprocessing
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables and set up OpenAI API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_audio_stream_url(youtube_url):
    """Extract the direct audio stream URL from a YouTube livestream URL using yt-dlp"""
    try:
        logger.info(f"Extracting audio stream URL from: {youtube_url}")

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            # Get stream info
            title = info.get("title", "Unknown Stream")
            channel = info.get("uploader", "Unknown Channel")
            viewers = info.get("view_count", 0)

            # Prepare stream info to return
            stream_info = {
                "title": title,
                "channel": channel,
                "viewers": str(viewers),
            }

            # Get the audio URL
            for format in info["formats"]:
                if format.get("acodec") != "none" and format.get("vcodec") == "none":
                    logger.info("Successfully extracted audio stream URL")
                    return format["url"], stream_info

            # If no audio-only format is found, use the best available format
            logger.warning("No audio-only format found, using best available format")
            return info["formats"][0]["url"], stream_info

    except Exception as e:
        logger.error(f"Failed to extract audio stream URL: {str(e)}")
        raise


def extract_audio_chunk(audio_url, chunk_duration=15, start_time=0):
    """Extract a chunk of audio from the livestream using ffmpeg"""
    try:
        # Create a temporary file for the audio chunk
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_filename = temp_file.name
        temp_file.close()

        timestamp = format_timestamp(start_time)
        logger.info(f"Extracting audio chunk at {timestamp}")

        # Use ffmpeg to extract the audio chunk
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-ss",
            str(start_time),  # Start time
            "-i",
            audio_url,  # Input URL
            "-t",
            str(chunk_duration),  # Duration
            "-vn",  # No video
            "-acodec",
            "mp3",  # Audio codec
            "-ar",
            "16000",  # Audio sample rate
            "-ac",
            "1",  # Mono audio
            temp_filename,  # Output file
        ]

        process = subprocess.Popen(
            ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_message = f"ffmpeg error: {stderr.decode()}"
            logger.error(error_message)
            raise Exception(error_message)

        return temp_filename

    except Exception as e:
        logger.error(f"Failed to extract audio chunk: {str(e)}")
        raise


def _run_transcription(audio_file_path, result_queue):
    """Run transcription in a separate process to avoid gevent conflicts"""
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe(model="whisper-1", file=audio_file)
            result_queue.put({"text": transcript["text"]})
    except Exception as e:
        result_queue.put({"error": str(e)})


def transcribe_audio_chunk(audio_file_path):
    """Transcribe an audio chunk using OpenAI's Whisper API"""
    try:
        logger.info("Transcribing chunk...")

        # Use multiprocessing to isolate from gevent patching
        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()

        # Run transcription in a separate process
        process = ctx.Process(
            target=_run_transcription, args=(audio_file_path, result_queue)
        )

        process.start()
        process.join(timeout=30)  # Set a timeout for the process

        if process.is_alive():
            process.terminate()
            process.join()
            raise Exception("Transcription process timed out")

        if not result_queue.empty():
            result = result_queue.get()
            if "error" in result:
                raise Exception(result["error"])
            return result["text"]
        else:
            raise Exception("Transcription process failed with no result")

    except Exception as e:
        logger.error(f"Failed to transcribe audio: {str(e)}")
        raise
    finally:
        # Clean up the temporary file
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)


def format_timestamp(seconds):
    """Format seconds into HH:MM:SS timestamp"""
    return str(datetime.timedelta(seconds=int(seconds))).zfill(8)
