import cv2
import numpy as np
import tempfile

SEQ_LEN = 35
IMG_SIZE = 128  # your model input
CHANNELS = 3

def preprocess_video(video_bytes):
    # Save bytes temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(video_bytes)
        video_path = tmp.name

    cap = cv2.VideoCapture(video_path)
    frames = []

    # Read all frames
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # BGR -> RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
        frames.append(frame)

    cap.release()

    if len(frames) == 0:
        raise ValueError("Cannot read frames from video.")

    # Sample exactly 35 frames
    if len(frames) >= SEQ_LEN:
        indices = np.linspace(0, len(frames)-1, SEQ_LEN).astype(int)
        sampled = [frames[i] for i in indices]
    else:
        repeat = int(np.ceil(SEQ_LEN / len(frames)))
        sampled = (frames * repeat)[:SEQ_LEN]

    sampled = np.array(sampled, dtype=np.float32)
    # Normalize to range [-1, 1]
    sampled = (sampled / 127.5) - 1.0

    # final shape → (1, 35, 128, 128, 3)
    sampled = np.expand_dims(sampled, axis=0)

    return sampled
