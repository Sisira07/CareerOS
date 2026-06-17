import requests
import json

board_token = "stripe"
url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

response = requests.get(url)
data = response.json()

print(f"Total jobs: {len(data['jobs'])}")
print(json.dumps(data["jobs"][0], indent=2))