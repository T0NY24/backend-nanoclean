import threading
import time
import requests
import cv2
from io import BytesIO
from PIL import Image
import numpy as np
import camera_manager as camera
from model_loader import get_model, is_model_ready
from config import (
    DEFAULT_CONFIDENCE,
    MIN_DETECTION_INTERVAL,
    WEB_SERVICE_URL,
    MIN_BBOX_AREA
)
import torch

CONTAINER_MAPPING = {
    "organico": {
        "contenedor": "ORGANICO",
        "color": "VERDE",
        "instruccion": "Deposite en el contenedor VERDE (orgánico)"
    },
    "papel_carton": {
        "contenedor": "PAPEL_CARTON",
        "color": "GRIS",
        "instruccion": "Deposite en el contenedor GRIS (papel/cartón)"
    },
    "plastico": {
        "contenedor": "PLASTICO",
        "color": "AZUL",
        "instruccion": "Deposite en el contenedor AZUL (plástico)"
    }
}

class RealTimeClassifier:
    def __init__(self):
        self.running = False
        self.thread = None
        self.confidence_threshold = DEFAULT_CONFIDENCE
        self.min_detection_interval = MIN_DETECTION_INTERVAL
        self.last_detection_time = 0
        self.detection_callback = None
        self.last_class = None
        self.last_confidence = 0

    def set_confidence_threshold(self, threshold):
        self.confidence_threshold = threshold

    def set_detection_callback(self, callback):
        self.detection_callback = callback

    def _classify_frame(self, frame):
        if not is_model_ready():
            return None

        pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        model = get_model()

        # Inferencia con YOLO-World
        results = model.predict(pil_image, conf=self.confidence_threshold, verbose=False)

        if not results or len(results[0].boxes) == 0:
            return None

        boxes = results[0].boxes
        
        # Simulación de profundidad: Filtrar objetos que están muy lejos (área pequeña)
        xyxy = boxes.xyxy
        areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
        valid_indices = torch.where(areas >= MIN_BBOX_AREA)[0]
        
        if len(valid_indices) == 0:
            return None

        # Tomar la caja válida con mayor confianza
        valid_confs = boxes.conf[valid_indices]
        best_valid_idx = valid_indices[torch.argmax(valid_confs)].item()
        
        class_id = int(boxes.cls[best_valid_idx].item())
        confidence = float(boxes.conf[best_valid_idx].item())
        raw_class_name = results[0].names[class_id].lower()
        bbox = boxes.xyxy[best_valid_idx].tolist()

        CLASS_MAPPING = {
            "cardboard": "papel_carton",
            "cardboard box": "papel_carton",
            "paper": "papel_carton",
            "crumpled paper": "papel_carton",
            "crumpled piece of paper": "papel_carton",
            "white paper ball": "papel_carton",
            "wad of paper": "papel_carton",
            "plastic bottle": "plastico",
            "plastic cup": "plastico",
            "plastic container": "plastico",
            "food waste": "organico",
            "fruit": "organico",
            "vegetable": "organico",
            "banana peel": "organico",
            "apple core": "organico"
        }

        if raw_class_name not in CLASS_MAPPING:
            return None

        class_name = CLASS_MAPPING[raw_class_name]

        # DEBUG: Guardar el frame recortado que vio YOLO-World
        try:
            import os
            os.makedirs("debug_frames", exist_ok=True)
            filename = f"debug_frames/realtime_{class_name}_{confidence*100:.1f}_{int(time.time())}.jpg"
            final_cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(final_cv_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(final_cv_image, f"{class_name} {confidence:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.imwrite(filename, final_cv_image)
        except Exception as e:
            print("Error guardando debug frame realtime:", e)

        return {
            "class": class_name,
            "confidence": confidence,
            "class_id": class_id,
            "bbox": bbox
        }

    def _send_to_backend(self, detection):
        class_name = detection["class"]
        confidence = detection["confidence"]

        mapping = CONTAINER_MAPPING.get(class_name, {
            "contenedor": "DESCONOCIDO",
            "color": "N/A",
            "instruccion": "No se pudo clasificar el objeto"
        })

        payload = {
            "contenedor": mapping["contenedor"],
            "claseDetectada": class_name,
            "confianza": confidence,
            "color": mapping["color"],
            "instruccion": mapping["instruccion"],
            "bbox": detection.get("bbox")
        }

        try:
            response = requests.post(
                f"{WEB_SERVICE_URL}/api/clasificar/internal",
                json=payload,
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                if self.detection_callback:
                    self.detection_callback(result)
                return result
            else:
                print(f"Error enviando al backend: {response.status_code}")
        except Exception as e:
            print(f"Error conectando al backend: {e}")

        return None

    def _process_loop(self):
        frame_count = 0
        process_every_n_frames = 3

        while self.running:
            frame = camera.get_frame()

            if frame is None:
                time.sleep(0.1)
                continue

            frame_count += 1

            if frame_count % process_every_n_frames != 0:
                continue

            detection = self._classify_frame(frame)

            if detection:
                current_time = time.time()
                time_since_last = current_time - self.last_detection_time

                if (time_since_last >= self.min_detection_interval or
                    self.last_class != detection["class"]):

                    print(f"Detección de alta confianza: {detection['class']} "
                          f"({detection['confidence']:.2%})")

                    self._send_to_backend(detection)
                    self.last_detection_time = current_time
                    self.last_class = detection["class"]
                    self.last_confidence = detection["confidence"]

            time.sleep(0.01)

    def start(self):
        if self.running:
            return

        if not is_model_ready():
            print("Error: Modelo no está listo")
            return

        if not camera.is_camera_running():
            print("Error: La cámara no está corriendo. Ejecuta /camera/start primero.")
            return

        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
        print("Clasificación en tiempo real iniciada")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("Clasificación en tiempo real detenida")

    def is_running(self):
        return self.running

    def get_status(self):
        return {
            "running": self.running,
            "confidence_threshold": self.confidence_threshold,
            "min_detection_interval": self.min_detection_interval,
            "last_detection": {
                "class": self.last_class,
                "confidence": self.last_confidence
            } if self.last_class else None
        }


_classifier_instance = None
_classifier_lock = threading.Lock()


def get_real_time_classifier():
    global _classifier_instance
    if _classifier_instance is None:
        with _classifier_lock:
            if _classifier_instance is None:
                _classifier_instance = RealTimeClassifier()
    return _classifier_instance
