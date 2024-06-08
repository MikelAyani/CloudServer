from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# File to store the data
DATA_FILE = 'data_store.json'

# In-memory data store
data_store = {}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(data_store, f)

# Load data from file at startup
data_store = load_data()

@app.route('/api/<key>', methods=['GET'])
def get_data(key):
    # Load data from file before handling the request
    global data_store
    data_store = load_data()
    if key in data_store:
        return jsonify(data_store[key])
    else:
        return 'No data found for key: {}'.format(key), 404

@app.route('/api/<key>', methods=['POST'])
def store_data(key):
    if request.is_json:
        data = request.json
    else:
        data = request.data
    if not data or not isinstance(data, dict):
        return 'Invalid JSON data', 400
    data_store[key] = data
    save_data()  # Save data to file after updating the data store
    return jsonify({'message': 'Data stored for key: {}'.format(key), 'data': data})

@app.route('/api', methods=['GET'])
def list_data():
    # Load data from file before handling the request
    global data_store
    data_store = load_data()
    return jsonify(data_store)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
