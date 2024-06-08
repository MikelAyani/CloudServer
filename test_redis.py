from vercel_kv_sdk import KV
import json
import os

KEY = "test"

# ADD ENV VARS TO TEST!

# Initialize Redis connection
redis_client = KV()

redis_client.set(KEY, json.dumps({"data":"Hello World!"}))

print(redis_client.get(KEY))