const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());

app.get('/', (req, res) => {
    res.send('Hello World!');
  });

let weatherData = {};

app.post('/weather', (req, res) => {
    weatherData = req.body;
    res.send({ status: 'success' });
});

app.get('/get_weather', (req, res) => {
    res.send(weatherData);
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});

