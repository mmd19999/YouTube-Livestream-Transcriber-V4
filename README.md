# YouTube Livestream Transcriber

A real-time application that connects to YouTube livestreams, extracts audio, and provides accurate transcription using OpenAI's Whisper API with precise timestamping.

## Features

- Connect to any YouTube livestream using its URL
- Extract audio in 20-second chunks for optimal processing
- Transcribe audio using OpenAI's Whisper API
- Display transcriptions in real-time with accurate timestamps
- Real-world time-based timestamp system for reliable timing
- Debug console for monitoring the transcription process
- Multi-user support via WebSocket connections

## How It Works

### System Architecture

The application is built on a client-server architecture:

1. **Backend (Flask + Socket.IO + Gevent)**
   - Handles YouTube stream connections
   - Extracts audio chunks using FFmpeg
   - Processes transcription via OpenAI Whisper API
   - Broadcasts transcriptions to all connected clients
   - Uses gevent for efficient asynchronous operations

2. **Frontend (HTML, CSS, JavaScript)**
   - Provides user interface for connecting to streams
   - Displays real-time transcriptions with timestamps
   - Shows stream information (title, channel, viewer count)
   - Includes debug console for monitoring the process

### Transcription Process

1. **Stream Connection**
   - When a user submits a YouTube URL, the backend extracts the direct audio stream URL using yt-dlp
   - Stream metadata (title, channel, viewers) is sent to the frontend

2. **Audio Processing**
   - The system extracts 20-second audio chunks from the stream using FFmpeg
   - Each chunk is processed sequentially to maintain context
   - Audio is converted to an optimal format for the Whisper API

3. **Transcription**
   - Each audio chunk is sent to OpenAI's Whisper API
   - The API returns a text transcription of the spoken content
   - Transcription occurs in a separate process to avoid blocking

4. **Timestamp System**
   - **Real-World Timestamp Mechanism**: Instead of relying on fixed chunk durations which can drift due to variable processing times and overlaps, the system:
     - Records the exact system time when transcription begins
     - For each chunk, calculates elapsed time based on the current real-world time
     - Timestamps reflect actual elapsed time since transcription start
     - This prevents timestamp drift over long sessions

5. **Real-time Broadcasting**
   - Transcriptions with timestamps are immediately broadcast to all connected clients
   - Socket.IO ensures efficient real-time communication

### Error Handling

- Robust error handling for network issues, YouTube API changes, and transcription errors
- Detailed logging system for troubleshooting
- Graceful recovery from most common errors without user intervention

## Requirements

- Python 3.8+
- FFmpeg installed and accessible in your PATH
- Conda environment named "transcription"
- OpenAI API key

## Setup

1. Clone this repository:
   ```
   git clone <repository-url>
   cd youtube-livestream-transcriber
   ```

2. Set up the Conda environment:
   ```
   conda create -n transcription python=3.8
   conda activate transcription
   ```

3. Install backend dependencies:
   ```
   cd backend
   pip install -r requirements.txt
   ```

4. Set up your OpenAI API key:
   - Create a `.env` file in the `backend` directory
   - Add your OpenAI API key: `OPENAI_API_KEY=your-api-key-here`

5. Make sure FFmpeg is installed:
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg` or equivalent for your distribution

## Running the Application

1. Start the backend server:
   ```
   cd backend
   conda activate transcription
   python app.py
   ```

2. Open the frontend:
   - Navigate to `http://localhost:5000` in your web browser

## Usage

1. Enter a YouTube livestream URL in the input field
2. Click "Connect" to begin the transcription process
3. View real-time transcriptions in the transcription window
4. Toggle the debug console to view detailed logs
5. Click "Stop Transcription" to end the process

## Technical Details

### Key Components

1. **app.py**
   - Main Flask application with Socket.IO integration
   - Handles client connections and event processing
   - Manages the transcription thread with gevent
   - Implements the real-world timestamp system

2. **transcription.py**
   - Handles YouTube stream extraction with yt-dlp
   - Processes audio chunks with FFmpeg
   - Interfaces with OpenAI's Whisper API
   - Formats timestamps and audio data

3. **Socket.IO Events**
   - `connect_livestream`: Initiates connection to a YouTube livestream
   - `transcription`: Broadcasts transcription data to clients
   - `livestream_info`: Provides metadata about the stream
   - `stop_transcription`: Halts the transcription process
   - `debug_log`: Sends detailed logs to the frontend console

### Timestamp System Implementation

The system uses a real-world time approach for accurate timestamps:

```python
# Initialize timestamp reference point when transcription begins
transcription_start_time = datetime.datetime.now()

# For each transcription chunk, calculate elapsed time from start
current_real_time = datetime.datetime.now()
elapsed_seconds = (current_real_time - transcription_start_time).total_seconds()
timestamp = format_timestamp(int(elapsed_seconds))
```

This approach ensures:
- Timestamps remain accurate regardless of processing delays
- No cumulative drift over long sessions
- Consistent timing that matches real-world elapsed time

## Troubleshooting

- If you encounter issues with FFmpeg, ensure it's properly installed and accessible in your PATH
- Check the debug console for detailed error messages
- Verify that your OpenAI API key is valid and has sufficient credits
- For stream connection issues, ensure the YouTube URL is valid and the stream is publicly accessible
- If timestamps seem off, check your system clock

## Project Structure

```
.
├── frontend/
│   ├── index.html      # Main HTML file
│   ├── styles.css      # CSS styles
│   └── script.js       # Frontend JavaScript
└── backend/
    ├── app.py          # Flask server with Socket.IO
    ├── transcription.py # Transcription functionality
    ├── .env            # Environment variables (API keys)
    └── requirements.txt # Python dependencies
```

## License

MIT

## Acknowledgements

- [OpenAI Whisper](https://openai.com/research/whisper) for audio transcription
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube stream extraction
- [Flask](https://flask.palletsprojects.com/) and [Socket.IO](https://socket.io/) for the web server and real-time communication
- [FFmpeg](https://ffmpeg.org/) for audio processing 