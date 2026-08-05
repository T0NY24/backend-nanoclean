import os

CAMERA_CONFIG = {
    "droidcam": {
        "type": "usb",
        "device_id": 0,
        "width": 640,
        "height": 480
    },
    "usb": {
        "type": "usb",
        "device_id": 0,
        "width": 640,
        "height": 480
    },
    "ip": {
        "type": "rtsp",
        "url": os.getenv("IP_CAMERA_URL", "rtsp://admin:admin@192.168.1.100:554/stream"),
        "username": os.getenv("IP_CAMERA_USER", "admin"),
        "password": os.getenv("IP_CAMERA_PASS", "admin"),
        "fps": 10
    }
}

DEFAULT_CONFIDENCE = float(os.getenv("DEFAULT_CONFIDENCE", "0.10"))
MIN_DETECTION_INTERVAL = float(os.getenv("MIN_DETECTION_INTERVAL", "3"))
MIN_BBOX_AREA = float(os.getenv("MIN_BBOX_AREA", "15000")) # Área mínima para considerar que un objeto está "cerca" (ancho * alto en pixeles)

WEB_SERVICE_URL = os.getenv("WEB_SERVICE_URL", "http://localhost:3001")

def get_camera_config(camera_name):
    if camera_name not in CAMERA_CONFIG:
        raise ValueError(f"Cámara '{camera_name}' no encontrada. Opciones: {list(CAMERA_CONFIG.keys())}")
    return CAMERA_CONFIG[camera_name]
