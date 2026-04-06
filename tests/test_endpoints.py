# tests/test_endpoints.py
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_root():
    resp = requests.get(f"{BASE_URL}/")
    print(resp.json())

def test_video_predict(video_path):
    with open(video_path, "rb") as f:
        files = {"video": f}
        resp = requests.post(f"{BASE_URL}/video/predict", files=files)
        print(resp.json())

if __name__ == "__main__":
    test_root()
    # test_video_predict("test_video.mp4")
