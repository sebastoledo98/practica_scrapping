import requests
import os
import json

with open("api_keys_modelos.json", 'r') as f:
    creds = json.load(f)
    api_key = creds['grok']['api-key']

#api_key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)

print(response.json())
