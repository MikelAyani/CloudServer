const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

// Middleware to parse JSON
app.use(express.json());

// Log all incoming requests
app.use((req, res, next) => {
  console.log(`Incoming request: ${req.method} ${req.originalUrl}`);
  next();
});

app.get('/api', (req, res) => {
  console.log('GET /api called');
  res.send('Hello, GET request!');
});

app.post('/api', (req, res) => {
  console.log('POST /api called');
  const data = req.body;
  res.send(`Hello, POST request! You sent: ${JSON.stringify(data)}`);
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});

// Default 404 handler
app.use((req, res, next) => {
  console.log(`404 - Not Found: ${req.originalUrl}`);
  res.status(404).send('Page not found');
});
