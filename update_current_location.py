
import requests

# Define the server URL
server_url = "http://localhost:5000/api/current_location"

# Define the JSON data to send
data = {
    "location": {
        "latitude": "58.389606",
        "longitude": "13.847002",
    },
    }

# Send a POST request
response_post = requests.post(server_url, json=data)
print(f"POST response: {response_post.text}")

# Send a GET request to retrieve the data
response_get = requests.get(server_url)
print(f"GET response: {response_get.json()}")
