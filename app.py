from flask import Flask, request, jsonify

app = Flask(__name__)

weather_data = {}

@app.route('/weather', methods=['POST'])
def receive_weather():
    global weather_data
    weather_data = request.json
    return jsonify({"status": "success"}), 200

@app.route('/get_weather', methods=['GET'])
def get_weather():
    return jsonify(weather_data), 200

if __name__ == '__main__':
    app.run(port=5000)
