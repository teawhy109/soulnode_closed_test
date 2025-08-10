import requests

data = {
    "content": "Kobe cried on the phone and said he wanted to come home.",
    "bookmark": "Kobe Call"
}

response = requests.post("http://127.0.0.1:5000/bookmark", json=data)
print(response.status_code)
print(response.json())