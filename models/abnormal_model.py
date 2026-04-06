import numpy as np
from pathlib import Path
from config.settings import settings


class AbnormalModel:
    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or settings.MODEL_PATH
        self.model = None
        
        # 🎯 ADAPTIVE THRESHOLD INITIALIZATION
        self.adaptive_threshold = 0.161  # Start with fixed threshold
        self.abnormal_rate = 0.0
        self.prediction_count = 0
        self.abnormal_count = 0

    def load(self) -> bool:
        if self.model is not None:
            return True
        path = Path(self.model_path)
        if not path.exists():
            print(f"Model file not found at {path}")
            return False
        try:
            import tensorflow as tf
            from tensorflow.keras.layers import Layer

            class AttentionPooling(Layer):
                def call(self, inputs):
                    attn_out, attn_scores = inputs
                    weights = tf.nn.softmax(attn_scores, axis=1)
                    return tf.reduce_sum(attn_out * weights, axis=1)

                def compute_output_shape(self, input_shape):
                    return (input_shape[0][0], input_shape[0][-1])

            self.model = tf.keras.models.load_model(
                str(path),
                compile=False,
                custom_objects={'AttentionPooling': AttentionPooling}
            )
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None
            return False

    def is_loaded(self) -> bool:
        return self.model is not None

    def predict(self, frames_tensor):
        if not self.is_loaded():
            if not self.load():
                raise ValueError("Model not loaded.")

        # Ensure frames_tensor has batch dimension
        if len(frames_tensor.shape) == 4:
            frames_tensor = np.expand_dims(frames_tensor, axis=0)

        pred = self.model.predict(frames_tensor)
        confidence = float(pred[0][0])

        # 🎯 ADAPTIVE THRESHOLD LOGIC
        self.prediction_count += 1
        
        # Initial prediction with current threshold
        is_abnormal = confidence > self.adaptive_threshold
        
        if is_abnormal:
            self.abnormal_count += 1
        
        # Update abnormal rate
        self.abnormal_rate = self.abnormal_count / self.prediction_count
        
        # Adjust threshold based on abnormal rate (every 50 predictions)
        if self.prediction_count % 50 == 0:
            if self.abnormal_rate > 0.3:  # Too many abnormalities (>30%)
                self.adaptive_threshold += 0.01
                print(f"🔺 Threshold increased to {self.adaptive_threshold:.3f} (abnormal rate: {self.abnormal_rate:.3f})")
            elif self.abnormal_rate < 0.05:  # Too few abnormalities (<5%)
                self.adaptive_threshold -= 0.005
                print(f"🔻 Threshold decreased to {self.adaptive_threshold:.3f} (abnormal rate: {self.abnormal_rate:.3f})")
            
            # Keep threshold in reasonable range
            self.adaptive_threshold = np.clip(self.adaptive_threshold, 0.05, 0.5)
        
        # Final prediction with adjusted threshold
        is_abnormal = confidence > self.adaptive_threshold

        print(f"🎯 Prediction #{self.prediction_count}: confidence={confidence:.3f}, threshold={self.adaptive_threshold:.3f}, abnormal={is_abnormal}, rate={self.abnormal_rate:.3f}")

        return is_abnormal, confidence
