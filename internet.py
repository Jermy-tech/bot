import requests

try:
    response = requests.get("https://www.google.com")
    print("Connection successful:", response.status_code)
except requests.exceptions.RequestException as e:
    print("Connection failed:", e)
