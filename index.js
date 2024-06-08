const express = require('express');
const cors = require('cors');
const app = express();
const port = process.env.PORT || 3000;

// Middleware to enable CORS
app.use(cors());

// Middleware to parse JSON with error handling
app.use(express.json());

// In-memory data store
let dataStore = {};

// Log all incoming requests
app.use((req, res, next) => {
  console.log(`Incoming request: ${req.method} ${req.originalUrl}`);
  next();
});

// Flexible POST route to store data
app.post('/api/:key', (req, res) => {
  const key = req.params.key;
  const value = req.body;
  console.log(`POST /api/${key} called with data: ${JSON.stringify(value)}`);
  if (!value || typeof value !== 'object') {
    res.status(400).send('Invalid JSON data');
    return;
  }
  dataStore[key] = value;
  console.log(`Data stored for key ${key}: ${JSON.stringify(dataStore[key])}`);
  res.json({ message: `Data stored for key: ${key}`, data: value });
});

// Flexible GET route to retrieve data
app.get('/api/:key', (req, res) => {
  const key = req.params.key;
  console.log(`GET /api/${key} called`);
  const data = dataStore[key];
  if (data) {
    res.json({ "data": data });
  } else {
    res.status(404).send(`No data found for key: ${key}`);
  }
});

// List all stored data
app.get('/api', (req, res) => {
  console.log('GET /api called to list all data');
  res.json(dataStore);
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});

// Default 404 handler
app.use((req, res, next) => {
  console.log(`404 - Not Found: ${req.originalUrl}`);
  res.status(404).send('Page not found');
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  if (err.type === 'entity.parse.failed') {
    res.status(400).send(`Bad Request: ${err.message}`);
  } else {
    res.status(500).send('Internal Server Error');
  }
});
