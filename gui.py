import tkinter as tk
from tkinter import filedialog
import threading
import cv2
import tempfile
from routers.inference import run_inference
from config.settings import settings
import os
import shutil
 

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Abnormal Behavior Checker")
        self.geometry("420x200")
        self.label = tk.Label(self, text="Choose source")
        self.label.pack(pady=10)
        self.btn_cam = tk.Button(self, text="Use Camera", command=self.on_camera)
        self.btn_cam.pack(pady=5)
        self.btn_upload = tk.Button(self, text="Upload Video", command=self.on_upload)
        self.btn_upload.pack(pady=5)
        self.btn_open_log = tk.Button(self, text="Open Log CSV", command=self.open_log)
        self.btn_open_log.pack(pady=5)
        self.btn_save_log = tk.Button(self, text="Save Log As...", command=self.save_log_as)
        self.btn_save_log.pack(pady=5)
        self.result = tk.Label(self, text="")
        self.result.pack(pady=10)

    def set_busy(self, busy: bool):
        state = tk.DISABLED if busy else tk.NORMAL
        self.btn_cam.config(state=state)
        self.btn_upload.config(state=state)
        self.btn_open_log.config(state=state)
        self.btn_save_log.config(state=state)

    def on_camera(self):
        self.set_busy(True)
        threading.Thread(target=self.capture_camera, daemon=True).start()

    def capture_camera(self):
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.result.config(text="Cannot open camera")
                self.set_busy(False)
                return
            frames = []
            while len(frames) < 35:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
            cap.release()
            if len(frames) < 1:
                self.result.config(text="No frames captured")
                self.set_busy(False)
                return
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                h, w = frames[0].shape[0], frames[0].shape[1]
                out = cv2.VideoWriter(tmp.name, cv2.VideoWriter_fourcc(*"mp4v"), 10, (w, h))
                for f in frames:
                    out.write(f)
                out.release()
                video_bytes = open(tmp.name, "rb").read()
            res = run_inference(video_bytes, video_id="gui_cam")
            txt = f"Confidence: {res['confidence']:.2f} | Abnormal: {res['is_abnormal']}"
            self.result.config(text=txt)
        except Exception as e:
            self.result.config(text=str(e))
        finally:
            self.set_busy(False)

    def on_upload(self):
        path = filedialog.askopenfilename(title="Select Video", filetypes=[("Video files", "*.mp4;*.avi;*.mov;*.mkv"), ("All files", "*.*")])
        if not path:
            return
        self.set_busy(True)
        threading.Thread(target=self.process_file, args=(path,), daemon=True).start()

    def process_file(self, path: str):
        try:
            with open(path, "rb") as f:
                video_bytes = f.read()
            res = run_inference(video_bytes, video_id="gui_upload")
            txt = f"Confidence: {res['confidence']:.2f} | Abnormal: {res['is_abnormal']}"
            self.result.config(text=txt)
        except Exception as e:
            self.result.config(text=str(e))
        finally:
            self.set_busy(False)

    def open_log(self):
        try:
            if os.path.exists(settings.LOG_CSV_PATH):
                os.startfile(settings.LOG_CSV_PATH)
            else:
                self.result.config(text="Log file not found")
        except Exception as e:
            self.result.config(text=str(e))

    def save_log_as(self):
        try:
            if not os.path.exists(settings.LOG_CSV_PATH):
                self.result.config(text="Log file not found")
                return
            target = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if not target:
                return
            shutil.copyfile(settings.LOG_CSV_PATH, target)
            self.result.config(text="Log saved")
        except Exception as e:
            self.result.config(text=str(e))

if __name__ == "__main__":
    app = App()
    app.mainloop()
