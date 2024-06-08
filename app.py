from flask import Flask, request, jsonify
import redis
import os
import json

app = Flask(__name__)

# Environment variables for Vercel KV
KV_URL = os.getenv('KV_URL')

# Initialize Redis connection
redis_client = redis.from_url(KV_URL, decode_responses=True)

@app.route('/api/<key>', methods=['GET'])
def get_data(key):
    data = redis_client.get(key)
    if data:
        return jsonify(json.loads(data))
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
    redis_client.set(key, json.dumps(data))
    return jsonify({'message': 'Data stored for key: {}'.format(key), 'data': data})

@app.route('/api', methods=['GET'])
def list_data():
    keys = redis_client.keys('*')
    data_store = {key: json.loads(redis_client.get(key)) for key in keys}
    return jsonify(data_store)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
