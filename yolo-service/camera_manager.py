import cv2
import threading
import queue
import time
import numpy as np

class BaseCamera:
    def __init__(self):
        self.running = False
        self.thread = None
        self.frame_queue = queue.Queue(maxsize=2)
        self.current_frame = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        time.sleep(0.5)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def get_frame(self):
        if not self.running:
            return None
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return self.current_frame

    def _capture_loop(self):
        raise NotImplementedError


class USBCamera(BaseCamera):
    def __init__(self, device_id=0, width=640, height=480):
        super().__init__()
        self.device_id = device_id
        self.width = width
        self.height = height
        self.cap = None

    def _open(self):
        self.cap = cv2.VideoCapture(self.device_id)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

    def _close(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def _capture_loop(self):
        self._open()
        if not self.cap or not self.cap.isOpened():
            print(f"Error: No se pudo abrir cámara USB device {self.device_id}")
            self.running = False
            return

        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    pass
            else:
                time.sleep(0.01)

        self._close()

    def restart(self):
        self._close()
        time.sleep(0.5)
        self._open()


class RTSPCamera(BaseCamera):
    def __init__(self, url, fps=10):
        super().__init__()
        self.url = url
        self.fps = fps
        self.cap = None
        self.frame_time = 1.0 / fps

    def _open(self):
        self.cap = cv2.VideoCapture(self.url)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def _close(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def _capture_loop(self):
        self._open()
        if not self.cap or not self.cap.isOpened():
            print(f"Error: No se pudo abrir cámara RTSP {self.url}")
            self.running = False
            return

        while self.running:
            start_time = time.time()
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    pass
            else:
                print("RTSP connection lost, retrying...")
                time.sleep(2)
                self._open()
                continue

            elapsed = time.time() - start_time
            sleep_time = self.frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        self._close()


_camera = None
_camera_type = None
_camera_config = None


def start_camera(camera_type, config):
    global _camera, _camera_type, _camera_config

    if _camera:
        stop_camera()

    _camera_config = config

    if camera_type in ["usb", "droidcam"]:
        device_id = config.get("device_id", 0)
        width = config.get("width", 640)
        height = config.get("height", 480)
        _camera = USBCamera(device_id, width, height)
        _camera_type = camera_type

    elif camera_type == "ip":
        _camera = RTSPCamera(config["url"], config.get("fps", 10))
        _camera_type = "ip"

    else:
        raise ValueError(f"Tipo de cámara desconocido: {camera_type}")

    _camera.start()
    return _camera_type


def stop_camera():
    global _camera, _camera_type, _camera_config
    if _camera:
        _camera.stop()
        _camera = None
        _camera_type = None


def get_frame():
    if _camera:
        return _camera.get_frame()
    return None


def is_camera_running():
    return _camera is not None and _camera.running


def get_camera_status():
    return {
        "running": is_camera_running(),
        "type": _camera_type,
        "config": _camera_config
    }
