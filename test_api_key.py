import os
import requests
import json

# Get the Google API key from environment variable
api_key = "AIzaSyAs-YV7aY6FeT-u9jCJpk3vtt1qrVasfnU"

print(f"Testing Google API key: {api_key}")

# List available models
list_models_url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"

try:
    response = requests.get(list_models_url)
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        print("API key is valid!")
        models = response.json().get("models", [])
        print(f"Available models: {len(models)}")
        for model in models:
            print(f"- {model.get('name')}")
    else:
        print("API key is invalid or has issues.")
        print(response.text)
except Exception as e:
    print(f"Error testing API key: {str(e)}")