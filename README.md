# YouTube Livestream Transcriber

A simple application that connects to YouTube livestreams, extracts audio, and provides real-time transcription using OpenAI's Whisper API.

## Features

- Connect to any YouTube livestream using its URL
- Extract audio in 15-second chunks
- Transcribe audio using OpenAI's Whisper API
- Display transcriptions in real-time with timestamps
- Debug console for monitoring the transcription process

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
   - Navigate to `http://localhost:5001` in your web browser

## Usage

1. Enter a YouTube livestream URL in the input field
2. Click "Connect" to begin the transcription process
3. View real-time transcriptions in the transcription window
4. Toggle the debug console to view detailed logs
5. Click "Stop Transcription" to end the process

## Troubleshooting

- If you encounter issues with FFmpeg, ensure it's properly installed and accessible in your PATH
- Check the debug console for detailed error messages
- Verify that your OpenAI API key is valid and has sufficient credits

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