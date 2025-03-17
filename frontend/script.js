document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const livestreamUrlInput = document.getElementById('livestream-url');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const connectionStatus = document.getElementById('connection-status');
    const streamStatus = document.getElementById('stream-status');
    const clientsCount = document.getElementById('clients-count');
    const transcriptionWindow = document.getElementById('transcription-window');
    const topicWindow = document.getElementById('topic-window');
    const majorTopicWindow = document.getElementById('major-topic-window');
    const topicTabs = document.querySelectorAll('.topic-tab');
    const debugConsole = document.getElementById('debug-console');
    const debugContent = document.getElementById('debug-content');
    const clearDebugBtn = document.getElementById('clear-debug-btn');
    const toggleSettingsBtn = document.getElementById('toggle-settings');
    const settingsContent = document.getElementById('settings-content');
    const copyBtn = document.getElementById('copy-btn');
    const saveBtn = document.getElementById('save-btn');
    const clearBtn = document.getElementById('clear-btn');
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const statsToggleBtn = document.getElementById('stats-toggle-btn');

    // State
    let isConnected = false;
    let isTranscribing = false;
    let transcriptionText = '';
    let isDebugVisible = true; // Start with debug visible

    // Initialize debug console
    function initDebugConsole() {
        // Make debug console visible by default for troubleshooting
        debugConsole.classList.remove('hidden');

        // Set up the event listener for the debug console toggle button
        statsToggleBtn.addEventListener('click', function (e) {
            e.preventDefault();
            toggleDebugConsole();
        });
    }

    // Initialize debug console
    initDebugConsole();

    // Initialize topic tabs
    function initTopicTabs() {
        topicTabs.forEach(tab => {
            tab.addEventListener('click', function () {
                // Remove active class from all tabs
                topicTabs.forEach(t => t.classList.remove('active'));

                // Add active class to clicked tab
                this.classList.add('active');

                // Hide all content
                document.querySelectorAll('.topic-content').forEach(content => {
                    content.classList.remove('active');
                });

                // Show content for selected tab
                const targetId = this.getAttribute('data-target');
                const targetContent = document.querySelector(`.topic-content[data-id="${targetId}"]`);
                if (targetContent) {
                    targetContent.classList.add('active');
                }
            });
        });
    }

    // Initialize topic tabs
    initTopicTabs();

    // Log function for debug console
    function logToConsole(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = type === 'error' ? 'error-message' :
            type === 'success' ? 'success-message' : '';
        logEntry.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
        debugContent.appendChild(logEntry);
        debugContent.scrollTop = debugContent.scrollHeight;
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    // Add initial debug message
    logToConsole('Initializing YouTube Livestream Transcriber...', 'info');
    logToConsole('Debug console is now visible for troubleshooting', 'info');

    // Connect to WebSocket server
    const serverUrl = 'http://localhost:5000';
    logToConsole(`Attempting to connect to WebSocket server at ${serverUrl}`, 'info');
    console.log(`Connecting to WebSocket server at ${serverUrl}`);

    try {
        const socket = io(serverUrl, {
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            forceNew: true,
            timeout: 20000
        });

        // Debug all socket events
        socket.onAny((event, ...args) => {
            console.log(`[Socket Event] ${event}:`, args);
            logToConsole(`Socket Event: ${event}`, 'info');
        });

        // Clear debug console
        function clearDebugConsole() {
            debugContent.innerHTML = '';
            logToConsole('Debug console cleared');
        }

        // Toggle debug console visibility
        function toggleDebugConsole() {
            isDebugVisible = !isDebugVisible;

            if (isDebugVisible) {
                debugConsole.classList.remove('hidden');
                logToConsole('Debug console opened');
                statsToggleBtn.innerHTML = '<i class="fas fa-terminal"></i>';
                statsToggleBtn.title = 'Hide Debug Console';
                statsToggleBtn.classList.add('active');
            } else {
                debugConsole.classList.add('hidden');
                statsToggleBtn.innerHTML = '<i class="fas fa-terminal"></i>';
                statsToggleBtn.title = 'Show Debug Console';
                statsToggleBtn.classList.remove('active');
            }
        }

        // Update connection status
        function updateConnectionStatus(connected) {
            isConnected = connected;
            connectionStatus.textContent = connected ? 'Connected' : 'Disconnected';
            connectionStatus.className = connected ? 'connected' : 'disconnected';
        }

        // Update stream status
        function updateStreamStatus(active) {
            isTranscribing = active;
            streamStatus.textContent = active ? 'Active' : 'Inactive';
            streamStatus.className = active ? 'active' : 'inactive';
            startBtn.disabled = active;
            stopBtn.disabled = !active;
        }

        // Add transcription entry
        function addTranscription(timestamp, text) {
            console.log('Received transcription:', timestamp, text);

            // Clear waiting message if present
            const waitingMsg = transcriptionWindow.querySelector('.waiting-message');
            if (waitingMsg) {
                transcriptionWindow.removeChild(waitingMsg);
            }

            const entry = document.createElement('div');

            // Format the text with better spacing and punctuation
            let formattedText = text;
            if (!text.match(/[.!?]$/)) {
                formattedText += '.';
            }

            entry.innerHTML = `<span class="timestamp">${timestamp}</span> ${formattedText}`;
            transcriptionWindow.appendChild(entry);
            transcriptionWindow.scrollTop = transcriptionWindow.scrollHeight;

            // Add to full transcription text
            transcriptionText += `[${timestamp}] ${text}\n`;

            // Also log to debug console
            logToConsole(`Transcription: ${timestamp} - ${text}`, 'success');
        }

        // Add topic change entry
        function addTopicChange(timestamp, topic) {
            // Clear no topics message if present
            const noTopics = topicWindow.querySelector('.no-topics');
            if (noTopics) {
                topicWindow.innerHTML = '';
            }

            const entry = document.createElement('div');
            entry.className = 'topic-change';

            // Format the topic with better capitalization
            const formattedTopic = topic.charAt(0).toUpperCase() + topic.slice(1);

            entry.innerHTML = `<span class="timestamp">${timestamp}</span> <strong>New Topic:</strong> ${formattedTopic}`;
            topicWindow.appendChild(entry);
            topicWindow.scrollTop = topicWindow.scrollHeight;
        }

        // Add major topic change entry
        function addMajorTopicChange(interval, topic) {
            // Clear no topics message if present
            const noTopics = majorTopicWindow.querySelector('.no-topics');
            if (noTopics) {
                majorTopicWindow.innerHTML = '';
            }

            const entry = document.createElement('div');
            entry.className = 'major-topic-change';

            // Format the topic with better capitalization
            const formattedTopic = topic.charAt(0).toUpperCase() + topic.slice(1);

            entry.innerHTML = `<span class="interval">${interval}</span> <strong>Major Topic:</strong> ${formattedTopic}`;
            majorTopicWindow.appendChild(entry);
            majorTopicWindow.scrollTop = majorTopicWindow.scrollHeight;

            // Also log to debug console
            logToConsole(`Major topic detected: ${topic} for interval ${interval}`, 'success');
        }

        // Start transcription
        function startTranscription() {
            const url = livestreamUrlInput.value.trim();

            if (!url) {
                logToConsole('Please enter a YouTube livestream URL', 'error');
                return;
            }

            logToConsole(`Connecting to livestream: ${url}`);

            // Send connection request to server
            socket.emit('connect_livestream', { url });
        }

        // Stop transcription
        function stopTranscription() {
            logToConsole('Stopping transcription');
            socket.emit('stop_transcription');
            updateStreamStatus(false);
        }

        // Copy transcription to clipboard
        function copyTranscription() {
            if (!transcriptionText) {
                logToConsole('No transcription to copy', 'error');
                return;
            }

            navigator.clipboard.writeText(transcriptionText)
                .then(() => {
                    logToConsole('Transcription copied to clipboard', 'success');
                })
                .catch(err => {
                    logToConsole(`Error copying to clipboard: ${err}`, 'error');
                });
        }

        // Save transcription to file
        function saveTranscription() {
            if (!transcriptionText) {
                logToConsole('No transcription to save', 'error');
                return;
            }

            const blob = new Blob([transcriptionText], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `transcription-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            logToConsole('Transcription saved to file', 'success');
        }

        // Clear transcription
        function clearTranscription() {
            transcriptionWindow.innerHTML = '<div class="waiting-message">Waiting for transcription...</div>';
            transcriptionText = '';
            logToConsole('Transcription cleared');
        }

        // Toggle settings
        function toggleSettings() {
            settingsContent.classList.toggle('hidden');
            toggleSettingsBtn.textContent = settingsContent.classList.contains('hidden') ? 'Show Settings' : 'Hide Settings';
        }

        // Toggle dark/light theme
        function toggleTheme() {
            document.body.classList.toggle('dark-theme');
            const isDarkTheme = document.body.classList.contains('dark-theme');
            themeToggleBtn.innerHTML = isDarkTheme ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
            localStorage.setItem('dark-theme', isDarkTheme);
        }

        // Check for saved theme preference
        function checkThemePreference() {
            if (localStorage.getItem('dark-theme') === 'true') {
                toggleTheme();
            }
        }

        // Event Listeners
        startBtn.addEventListener('click', startTranscription);
        stopBtn.addEventListener('click', stopTranscription);
        copyBtn.addEventListener('click', copyTranscription);
        saveBtn.addEventListener('click', saveTranscription);
        clearBtn.addEventListener('click', clearTranscription);
        clearDebugBtn.addEventListener('click', clearDebugConsole);
        toggleSettingsBtn.addEventListener('click', toggleSettings);
        themeToggleBtn.addEventListener('click', toggleTheme);

        // Check theme preference on load
        checkThemePreference();

        // Socket event listeners
        socket.on('connect', () => {
            logToConsole('Connected to server', 'success');
            updateConnectionStatus(true);
        });

        socket.on('disconnect', () => {
            logToConsole('Disconnected from server', 'error');
            updateConnectionStatus(false);
            updateStreamStatus(false);
        });

        socket.on('connect_error', (err) => {
            logToConsole(`Connection error: ${err.message}`, 'error');
            updateConnectionStatus(false);
        });

        socket.on('clients_update', (data) => {
            clientsCount.textContent = data.count;
            logToConsole(`Connected clients: ${data.count}`);
        });

        socket.on('livestream_connected', (data) => {
            logToConsole(`Connected to livestream: ${data.url}`, 'success');
        });

        socket.on('livestream_error', (data) => {
            logToConsole(`Livestream error: ${data.message}`, 'error');
            updateStreamStatus(false);
        });

        socket.on('livestream_info', (data) => {
            logToConsole(`Stream info received: ${data.title} by ${data.channel}`, 'info');
            updateStreamStatus(true);
        });

        socket.on('transcription', (data) => {
            addTranscription(data.timestamp, data.text);
        });

        // Add handler for topic change events
        socket.on('topic_change', (data) => {
            logToConsole(`Topic change detected: ${data.topic} at ${data.timestamp}`, 'success');
            addTopicChange(data.timestamp, data.topic);
        });

        // Add handler for major topic change events
        socket.on('major_topic_change', (data) => {
            logToConsole(`Major topic detected: ${data.topic} for interval ${data.interval}`, 'success');
            addMajorTopicChange(data.interval, data.topic);
        });

        socket.on('debug_log', (data) => {
            logToConsole(data.message, data.type || 'info');
        });

        // Log initial message
        logToConsole('Socket.IO connection initialized', 'info');
    } catch (error) {
        console.error('Error initializing Socket.IO:', error);
        logToConsole(`Error initializing Socket.IO: ${error.message}`, 'error');
        updateConnectionStatus(false);
    }
}); 