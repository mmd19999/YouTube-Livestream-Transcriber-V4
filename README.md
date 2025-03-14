# YouTube Livestream Transcriber

A clean, modern web UI for transcribing YouTube livestreams with topic change detection.

## Features

- Real-time transcription of YouTube livestreams
- Topic change detection and summary
- Live transcription display with copy, save, and clear functionality
- Status indicators for connection and stream status
- Settings panel for future customization options
- Debug console for monitoring system activities
- Responsive design for various screen sizes
- Light/dark theme toggle (UI only, functionality to be implemented)

## Project Structure

```
.
├── frontend/
│   ├── index.html      # Main HTML file
│   ├── styles.css      # CSS styles
│   └── script.js       # Frontend JavaScript
└── backend/
    ├── app.py          # Flask server with Socket.IO
    └── requirements.txt # Python dependencies
```

## Setup Instructions

### Backend Setup

1. Make sure you have Python 3.7+ installed
2. Navigate to the backend directory:
   ```
   cd backend
   ```
3. Create and activate a conda environment:
   ```
   conda create -n transcribtion python=3.9 -y
   conda activate transcribtion
   ```
4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
5. Start the Flask server:
   ```
   python app.py
   ```
   The server will run on http://localhost:5000

### Frontend Access

Once the backend server is running, you can access the application by:

1. Opening a web browser
2. Navigating to http://localhost:5000

## Usage

1. Enter a YouTube livestream URL in the input field
2. Click the "Start Transcription" button to begin
3. View real-time transcription in the Live Transcription panel
4. Monitor topic changes in the Topic Summary panel
5. Use the Copy, Save, or Clear buttons to manage the transcription
6. Click "Stop Transcription" to end the process

## Features to Implement

This is a demonstration application with mock data. In a production environment, you would need to implement:

1. Actual YouTube livestream connection using the youtube-dl library
2. Audio extraction from the livestream
3. Real-time transcription using a speech-to-text service
4. Topic change detection using NLP techniques
5. User authentication and saved transcriptions
6. Dark/light theme toggle functionality
7. Settings panel with transcription options

## License

MIT 