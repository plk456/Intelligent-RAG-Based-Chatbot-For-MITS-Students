const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware to serve static files from the template directory
app.use(express.static(path.join(__dirname, 'template')));

// Route to serve the main chatbot page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'template', 'chatbot_mits.html'));
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Chatbot server is running' });
});

// Start the server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Chatbot server is running on port ${PORT}`);
  console.log(`Access the chatbot at http://localhost:${PORT}`);
});