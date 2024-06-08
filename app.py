from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory data store
data_store = {}

@app.route('/api/<key>', methods=['GET'])
def get_data(key):
    if key in data_store:
        return jsonify({key: data_store[key]})
    else:
        return 'No data found for key: {}'.format(key), 404

@app.route('/api/<key>', methods=['POST'])
def store_data(key):
    data = request.json
    if not data or not isinstance(data, dict):
        return 'Invalid JSON data', 400
    data_store[key] = data
    return jsonify({'message': 'Data stored for key: {}'.format(key), 'data': data})

@app.route('/api', methods=['GET'])
def list_data():
    return jsonify(data_store)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)