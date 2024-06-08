from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

# Environment variables for Vercel KV REST API
KV_REST_API_URL = os.getenv('KV_REST_API_URL')
KV_REST_API_TOKEN = os.getenv('KV_REST_API_TOKEN')

def get_headers():
    return {
        'Authorization': f'Bearer {KV_REST_API_TOKEN}',
        'Content-Type': 'application/json'
    }

@app.route('/api/<key>', methods=['GET'])
def get_data(key):
    response = requests.get(f'{KV_REST_API_URL}/get/{key}', headers=get_headers())
    if response.status_code == 200:
        data = response.json().get('result')
        if data:
            return jsonify(json.loads(data))
    return 'No data found for key: {}'.format(key), 404

@app.route('/api/<key>', methods=['POST'])
def store_data(key):
    if request.is_json:
        data = request.json
    else:
        data = request.data
    if not data or not isinstance(data, dict):
        return 'Invalid JSON data', 400
    payload = {
        'value': json.dumps(data)
    }
    response = requests.post(f'{KV_REST_API_URL}/set/{key}', headers=get_headers(), json=payload)
    if response.status_code == 200:
        return jsonify({'message': 'Data stored for key: {}'.format(key), 'data': data})
    return 'Failed to store data', 500

@app.route('/api', methods=['GET'])
def list_data():
    response = requests.get(f'{KV_REST_API_URL}/keys', headers=get_headers())
    if response.status_code == 200:
        keys = response.json().get('result', [])
        data_store = {key: json.loads(requests.get(f'{KV_REST_API_URL}/get/{key}', headers=get_headers()).json().get('result')) for key in keys}
        return jsonify(data_store)
    return 'Failed to list data', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
