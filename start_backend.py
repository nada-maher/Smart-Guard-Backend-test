# start_backend_single_terminal.py
import threading
from workers.stream_processor import process_video_stream

import uvicorn
import time
import asyncio

import shared_state

VIDEO_SOURCE = 0
VIDEO_ID = "cam1"

def run_backend():
    shared_state.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(shared_state.loop)
    config = uvicorn.Config("main:app", host="127.0.0.1", port=8001, loop="asyncio")
    server = uvicorn.Server(config)
    shared_state.loop.run_until_complete(server.serve())

def run_stream():
    time.sleep(3)  # Increased wait time for backend and event loop to initialize
    print("Starting stream processor with preprocessing and 35-frame analysis...")
    try:
        process_video_stream(video_source=VIDEO_SOURCE, video_id=VIDEO_ID)
    except Exception as e:
        print("Error in video stream:", e)

if __name__ == "__main__":
    # Run backend in a daemon thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # Run video stream in main thread
    stream_thread = threading.Thread(target=run_stream)
    stream_thread.start()

    # Wait for threads
    backend_thread.join()
    stream_thread.join()
