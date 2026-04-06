# backend/services/frame_store.py

latest_jpeg = None
latest_pred = None

def set_jpeg(jpeg_bytes):
    global latest_jpeg
    latest_jpeg = jpeg_bytes

def get_jpeg():
    global latest_jpeg
    # Directly return whatever is in latest_jpeg
    return latest_jpeg

def set_prediction(pred):
    global latest_pred
    latest_pred = pred

def get_prediction():
    return latest_pred
