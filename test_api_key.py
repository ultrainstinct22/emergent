import os
import requests
import json

# Get the Google API key from environment variable
api_key = "AIzaSyAs-YV7aY6FeT-u9jCJpk3vtt1qrVasfnU"

print(f"Testing Google API key: {api_key}")

# Test the API key with a simple Gemini API request
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"

payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": "Hello, can you verify that this API key is working?"
                }
            ]
        }
    ]
}

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        print("API key is valid!")
        print(json.dumps(response.json(), indent=2))
    else:
        print("API key is invalid or has issues.")
        print(response.text)
except Exception as e:
    print(f"Error testing API key: {str(e)}")