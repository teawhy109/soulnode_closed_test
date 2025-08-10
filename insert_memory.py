import requests

data = {
    "content": "Ty once weighed 375 pounds and is now healing through fasting.",
    "type": "private"
}

response = requests.post("http://127.0.0.1:5000/save", json=data)
print(response.status_code)
print(response.json())