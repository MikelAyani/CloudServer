
import requests
url = 'https://maiklof-http-server-chi.vercel.app/api/test'
json_data = {
    'Hello': 'World',
}

response = requests.post(url, json=json_data)
if response.status_code == 200:
    print('JSON data sent successfully!')
else:
    print('Failed to send JSON data:', response.status_code)

response = requests.get(url)
if response.status_code == 200:
    print('JSON data sent successfully!', response.text)
else:
    print('Failed to send JSON data:', response.status_code)
