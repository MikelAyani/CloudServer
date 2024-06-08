
import requests

# Define the server URL
#server_url = "https://maiklof-http-server-chi.vercel.app/api/weather_today"
server_url = "http://localhost:5000/api/weather_today"

# Define the JSON data to send
data = 	{"data":{
        "Icon":"http://openweathermap.org/img/w/10d.png",
        "Rain":"7.98",
        "Cloudiness":"96",
        "Description":"moderate rain",
        "Air humidity":"84",
        "Atmospheric pressure":"1006",
        }
}


# Send a POST request
response_post = requests.post(server_url, json=data)
print(f"POST response: {response_post.text}")

# Send a GET request to retrieve the data
response_get = requests.get(server_url)
print(f"GET response: {response_get.json()}")
