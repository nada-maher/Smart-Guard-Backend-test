try:

    from models.abnormal_model import AbnormalModel

    from utils.preprocessing import preprocess_video

    

    class AbnormalBehaviorDetector:

        def __init__(self):

            self.model = AbnormalModel()



        def predict(self, video_bytes):

            frames_tensor = preprocess_video(video_bytes)

            is_abnormal, confidence = self.model.predict(frames_tensor)



            return {

                "is_abnormal": is_abnormal,

                "confidence": confidence

            }

except ImportError:

    # Fallback to TensorFlow-free detector

    from .tensorflow_free_detector import TensorFlowFreeAbnormalBehaviorDetector

    

    class AbnormalBehaviorDetector:

        def __init__(self):

            self.detector = TensorFlowFreeAbnormalBehaviorDetector()



        def predict(self, video_bytes):

            return self.detector.predict(video_bytes)

