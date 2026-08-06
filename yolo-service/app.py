from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.responses import StreamingResponse
from pathlib import Path
import threading
import json
import asyncio

from classifier import classify_image
from model_loader import load_model, is_model_ready
import camera_manager as camera
from real_time_classifier import get_real_time_classifier
from config import get_camera_config, DEFAULT_CONFIDENCE, MIN_DETECTION_INTERVAL
from video_stream import generate_frames

app = FastAPI(
    title="NanoClean YOLO Service",
    description="Microservicio de clasificación de basura usando YOLOv8",
    version="1.3.0"
)

origins = [
    "https://nanoclean.uidehub.tech",
    "https://api-nano-clean.uidehub.tech",
    "https://api-yolo.uidehub.tech",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3006",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3006",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "templates"
TEMPLATE_DIR.mkdir(exist_ok=True)


@app.on_event("startup")
async def startup_event():
    try:
        load_model()
        print("✅ Modelo YOLO cargado exitosamente")
    except FileNotFoundError as e:
        print(f"⚠️ Advertencia: {e}")
        print("   El servicio iniciado pero la clasificación no funcionará hasta que copies el modelo.")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = TEMPLATE_DIR / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return """
    <html>
    <head><title>NanoClean</title></head>
    <body>
        <h1>NanoClean YOLO Service</h1>
        <p>Servicio corriendo. Usa /camera/start para iniciar la cámara.</p>
        <p>Usa /video_feed para ver el stream de video.</p>
    </body>
    </html>
    """


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/health")
async def health():
    classifier = get_real_time_classifier()
    return {
        "status": "healthy",
        "model_ready": is_model_ready(),
        "camera_running": camera.is_camera_running(),
        "classifier_running": classifier.is_running()
    }


@app.post("/classify")
async def classify(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    try:
        image_bytes = await file.read()
        result = classify_image(image_bytes)

        if not result.get("success"):
            return JSONResponse(
                status_code=200,
                content=result
            )

        return result

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno: {str(e)}"
            }
        )


@app.post("/classify/base64")
async def classify_base64(payload: dict):
    if "image" not in payload:
        raise HTTPException(status_code=400, detail="Falta el campo 'image' con base64")

    try:
        import base64
        import requests
        from config import WEB_SERVICE_URL
        
        # Eliminar el encabezado data:image/jpeg;base64, si viene desde el frontend
        image_data = payload["image"]
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
            
        image_bytes = base64.b64decode(image_data)
        result = classify_image(image_bytes)

        if not result.get("success"):
            return JSONResponse(
                status_code=200,
                content=result
            )

        # Enviar resultado al backend Express para guardarlo en DB y WebSocket
        try:
            backend_payload = {
                "contenedor": result["contenedor"],
                "claseDetectada": result["detection"]["class"],
                "confianza": result["detection"]["confidence"],
                "color": result["color"],
                "instruccion": result["instruccion"],
                "bbox": result["detection"].get("bbox")
            }
            requests.post(
                f"{WEB_SERVICE_URL}/api/clasificar/internal",
                json=backend_payload,
                timeout=5
            )
        except Exception as err:
            print(f"Advertencia: No se pudo enviar resultado a Node.js: {err}")

        return result

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Error interno: {str(e)}"
            }
        )


@app.post("/camera/start")
async def camera_start(payload: dict):
    camera_name = payload.get("camera", "droidcam")

    try:
        config = get_camera_config(camera_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        camera_type = camera.start_camera(camera_name, config)
        return {
            "success": True,
            "message": f"Cámara {camera_name} iniciada ({camera_type})",
            "status": camera.get_camera_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error iniciando cámara: {str(e)}")


@app.post("/camera/stop")
async def camera_stop():
    classifier = get_real_time_classifier()
    classifier.stop()
    camera.stop_camera()

    return {
        "success": True,
        "message": "Cámara y clasificador detenidos",
        "status": camera.get_camera_status()
    }


@app.post("/camera/switch")
async def camera_switch(payload: dict):
    camera_name = payload.get("camera")

    if not camera_name:
        raise HTTPException(status_code=400, detail="Falta el campo 'camera'")

    classifier = get_real_time_classifier()
    classifier.stop()

    try:
        config = get_camera_config(camera_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        camera_type = camera.start_camera(camera_name, config)
        return {
            "success": True,
            "message": f"Cambiado a cámara {camera_name} ({camera_type})",
            "status": camera.get_camera_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cambiando cámara: {str(e)}")


@app.get("/camera/status")
async def camera_status():
    classifier = get_real_time_classifier()
    return {
        "camera": camera.get_camera_status(),
        "classifier": classifier.get_status()
    }


@app.get("/camera/config")
async def camera_config_get():
    classifier = get_real_time_classifier()
    return {
        "confidence_threshold": classifier.confidence_threshold,
        "min_detection_interval": classifier.min_detection_interval,
        "available_cameras": ["droidcam", "usb", "ip"],
        "current_camera": camera._camera_type
    }


@app.patch("/camera/config")
async def camera_config_update(payload: dict):
    classifier = get_real_time_classifier()

    if "confidence" in payload:
        confidence = float(payload["confidence"])
        if 0 < confidence <= 1:
            classifier.set_confidence_threshold(confidence)
        else:
            raise HTTPException(
                status_code=400,
                detail="confidence debe estar entre 0 y 1"
            )

    if "min_detection_interval" in payload:
        interval = float(payload["min_detection_interval"])
        if interval > 0:
            classifier.min_detection_interval = interval
        else:
            raise HTTPException(
                status_code=400,
                detail="min_detection_interval debe ser mayor a 0"
            )

    return {
        "success": True,
        "config": {
            "confidence_threshold": classifier.confidence_threshold,
            "min_detection_interval": classifier.min_detection_interval
        }
    }


@app.post("/classifier/start")
async def classifier_start():
    classifier = get_real_time_classifier()

    if not camera.is_camera_running():
        raise HTTPException(
            status_code=400,
            detail="La cámara no está corriendo. Ejecuta /camera/start primero."
        )

    try:
        classifier.start()
        return {
            "success": True,
            "message": "Clasificación en Tiempo Real iniciada",
            "status": classifier.get_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/classifier/stop")
async def classifier_stop():
    classifier = get_real_time_classifier()
    classifier.stop()

    return {
        "success": True,
        "message": "Clasificación en Tiempo Real detenida",
        "status": classifier.get_status()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)


# WebSocket support
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back para confirmar
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def broadcast_detection(detection: dict):
    """Función para emitir detecciones a todos los clientes WebSocket"""
    asyncio.create_task(manager.broadcast(detection))
