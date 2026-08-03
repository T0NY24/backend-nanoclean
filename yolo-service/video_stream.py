import cv2
import numpy as np
import threading
import time
import queue
from PIL import Image
import camera_manager as camera
import model_loader

CONTAINER_COLORS = {
    "organico": (0, 255, 0),      # Verde
    "papel_carton": (128, 128, 128),  # Gris
    "plastico": (255, 0, 0),        # Azul
}

CONTAINER_NAMES = {
    "organico": "ORGANICO",
    "papel_carton": "PAPEL/CARTON",
    "plastico": "PLASTICO",
}

class VideoStream:
    def __init__(self):
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        self.current_detection = None
        self.last_update = 0

    def update_frame(self, frame, detection=None):
        with self.lock:
            self.frame = frame.copy() if frame is not None else None
            if detection:
                self.current_detection = detection

    def get_frame(self):
        with self.lock:
            return self.frame

    def get_detection(self):
        with self.lock:
            return self.current_detection


_video_stream = VideoStream()


def draw_detection(frame, detection):
    if detection is None:
        return frame

    if frame is None:
        return None

    class_name = detection.get("class", "unknown")
    confidence = detection.get("confidence", 0)
    container = detection.get("container", class_name)

    color = CONTAINER_COLORS.get(class_name, (255, 255, 255))

    h, w = frame.shape[:2]

    label = f"{CONTAINER_NAMES.get(class_name, class_name.upper())} {confidence:.1%}"

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2

    (text_width, text_height), baseline = cv2.getTextSize(
        label, font, font_scale, thickness
    )

    cv2.rectangle(frame, (10, 10), (text_width + 20, text_height + 30), color, -1)

    cv2.putText(frame, label, (15, text_height + 18),
                font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    return frame


def generate_frames():
    global _video_stream
    frame_count = 0

    while True:
        frame = camera.get_frame()

        if frame is None:
            time.sleep(0.1)
            continue

        frame_count += 1

        if frame_count % 5 == 0:
            _video_stream.update_frame(frame)
        else:
            with _video_stream.lock:
                _video_stream.frame = frame

        detection = None
        if model_loader.is_model_ready() and frame_count % 10 == 0:
            try:
                model = model_loader.get_model()
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                results = model.predict(source=pil_image, conf=0.5, verbose=False)

                if results and len(results) > 0:
                    result = results[0]
                    if result.probs is not None:
                        class_id = int(result.probs.top1)
                        confidence = float(result.probs.top1conf)
                        class_name = result.names[class_id]

                        detection = {
                            "class": class_name,
                            "confidence": confidence,
                            "container": class_name
                        }

                        _video_stream.current_detection = detection
            except Exception as e:
                print(f"Error en detección: {e}")

        annotated_frame = draw_detection(frame, detection)

        if annotated_frame is not None:
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        time.sleep(0.03)


def get_video_stream():
    return _video_stream
