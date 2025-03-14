// Simple test script to verify Socket.IO connection
console.log('Starting Socket.IO connection test...');

// Check if Socket.IO is loaded
if (typeof io === 'undefined') {
    console.error('Socket.IO is not loaded. Make sure the Socket.IO client library is included.');
} else {
    console.log('Socket.IO is loaded. Attempting to connect...');

    // Connect to the Socket.IO server
    const socket = io('http://localhost:5000', {
        transports: ['websocket', 'polling'],
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        forceNew: true,
        timeout: 10000
    });

    // Connection events
    socket.on('connect', () => {
        console.log('Connected to server!');
        console.log('Socket ID:', socket.id);

        // Send a test ping
        socket.emit('ping', { message: 'Testing connection' });
        console.log('Sent ping to server');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from server');
    });

    socket.on('connect_error', (error) => {
        console.error('Connection error:', error.message);
    });

    socket.on('pong', (data) => {
        console.log('Received pong from server:', data);
    });

    // Listen for any event
    socket.onAny((event, ...args) => {
        console.log(`Received event: ${event}`, args);
    });
}

console.log('Socket.IO connection test initialized'); 