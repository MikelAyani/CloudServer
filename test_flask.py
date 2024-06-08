
import requests
url = 'http://localhost:5000/api/test'
#url = 'https://maiklof-http-server-chi.vercel.app/api/test'
json_data = {
    'Hello': 'World',
}


response = requests.get(url)
if response.status_code == 200:
    print('JSON data sent successfully!', response.text)
else:
    print('Failed to send JSON data:', response.status_code)
