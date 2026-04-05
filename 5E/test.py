import requests
import json
import sys


def main():
    url = "http://localhost:8000/chat/message"
    
    payload = {
        "user_id": "test_user_002",
        "lesson_id": "lesson_101",
        "content": ""
    }
    
    print(f"Connecting to {url}...")
    try:
        with requests.post(url, json=payload, stream=True) as response:
            if response.status_code == 200:
                print("Response stream started:")
                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        print(chunk, end='', flush=True)
                print("\nStream finished.")
            else:
                print(f"Request failed with status: {response.status_code}\n{response.text}")
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure main.py is running on port 8000.")

if __name__ == "__main__":
    main()