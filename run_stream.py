# run_stream_debug.py
import cv2
from routers.inference import run_inference
import tempfile
from services.frame_store import frame_store

VIDEO_SOURCE = 0      # 0 = webcam or path to video
VIDEO_ID = "cam1"     # video ID for Redis or storage
SEQ_LEN = 35          # number of frames per inference

def process_video_stream_debug(video_source=VIDEO_SOURCE, video_id=VIDEO_ID, show_window=True):
    print("Opening video source:", video_source)
    cap = cv2.VideoCapture(video_source)

    if not cap.isOpened():
        print("Error: Cannot open video source")
        return

    frames = []
    print("Video source opened successfully. Starting frame capture...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("No more frames received, ending stream.")
                break

            print("Frame received")
            try:
                ok, buf = cv2.imencode(".jpg", frame)
                if ok:
                    frame_store.set_jpeg(buf.tobytes())
            except Exception:
                pass
            frames.append(frame)

            # Run inference when we have SEQ_LEN frames
            if len(frames) >= SEQ_LEN:
                print(f"{SEQ_LEN} frames collected, running inference...")
                try:
                    # Save frames temporarily to MP4
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                        out = cv2.VideoWriter(
                            tmp.name,
                            cv2.VideoWriter_fourcc(*'mp4v'),
                            10,
                            (frames[0].shape[1], frames[0].shape[0])
                        )
                        for f in frames:
                            out.write(f)
                        out.release()
                        video_bytes = open(tmp.name, "rb").read()

                    # Run inference
                    result = run_inference(video_bytes, video_id=video_id)
                    print("Inference Result:", result)

                except Exception as e:
                    print("Error during inference:", e)

                frames = []  # reset buffer

            # Optional: display video
            if show_window:
                cv2.imshow("Debug Stream", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Stream interrupted by user")
                    break

    finally:
        cap.release()
        if show_window:
            cv2.destroyAllWindows()
        print("Video stream ended.")

# -------------------------------
if __name__ == "__main__":
    print("Starting debug real-time video processing...")
    process_video_stream_debug()
