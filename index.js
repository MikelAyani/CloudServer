const express = require('express');
const cors = require('cors');
const app = express();
const port = process.env.PORT || 3000;

// Middleware to enable CORS
app.use(cors());

// Middleware to parse JSON
app.use(express.json());

// In-memory data store
let dataStore = {};

// Log all incoming requests
app.use((req, res, next) => {
  console.log(`Incoming request: ${req.method} ${req.originalUrl}`);
  next();
});

// Flexible GET route to retrieve data
app.get('/api/:key', (req, res) => {
  const key = req.params.key;
  console.log(`GET /api/${key} called`);
  const data = dataStore[key];
  if (data) {
    res.json({"data":data});
  } else {
    res.status(404).send(`No data found for key: ${key}`);
  }
});

// Flexible POST route to store data
app.post('/api/:key', (req, res) => {
  const key = req.params.key;
  const value = req.body;
  console.log(`POST /api/${key} called with data: ${JSON.stringify(value)}`);
  dataStore[key] = value;
  res.json({ message: `Data stored for key: ${key}`, data: value });
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
