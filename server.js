const express = require('express');
const path = require('path');
const { MongoClient } = require('mongodb');

// MongoDB connection
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017';
const DB_NAME = 'mits_chatbot';
const COLLECTION_NAME = 'conversations';

let db;
let client;

// Connect to MongoDB
async function connectToMongo() {
  try {
    client = new MongoClient(MONGODB_URI);
    await client.connect();
    db = client.db(DB_NAME);
    console.log('Connected to MongoDB');
  } catch (err) {
    console.error('Failed to connect to MongoDB:', err);
  }
}

// Connect to MongoDB on startup
connectToMongo();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware to serve static files from the template directory
app.use(express.static(path.join(__dirname, 'template')));
app.use(express.json()); // Add this to parse JSON bodies

// Route to serve the main chatbot page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'template', 'chatbot_mits.html'));
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Chatbot server is running' });
});

// API endpoint to save conversation
app.post('/api/conversations', async (req, res) => {
  try {
    if (!db) {
      return res.status(500).json({ error: 'Database not connected' });
    }
    
    const { userId, conversation } = req.body;
    
    if (!userId || !conversation) {
      return res.status(400).json({ error: 'userId and conversation are required' });
    }
    
    // Save conversation to MongoDB
    const collection = db.collection(COLLECTION_NAME);
    await collection.updateOne(
      { userId: userId },
      { $set: { userId: userId, conversation: conversation, updatedAt: new Date() } },
      { upsert: true }
    );
    
    res.status(200).json({ message: 'Conversation saved successfully' });
  } catch (err) {
    console.error('Error saving conversation:', err);
    res.status(500).json({ error: 'Failed to save conversation' });
  }
});

// API endpoint to load conversation
app.get('/api/conversations/:userId', async (req, res) => {
  try {
    if (!db) {
      return res.status(500).json({ error: 'Database not connected' });
    }
    
    const { userId } = req.params;
    
    const collection = db.collection(COLLECTION_NAME);
    const result = await collection.findOne({ userId: userId });
    
    if (result) {
      res.status(200).json({ conversation: result.conversation });
    } else {
      res.status(200).json({ conversation: [] });
    }
  } catch (err) {
    console.error('Error loading conversation:', err);
    res.status(500).json({ error: 'Failed to load conversation' });
  }
});

// Start the server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`Chatbot server is running on port ${PORT}`);
  console.log(`Access the chatbot at http://localhost:${PORT}`);
});