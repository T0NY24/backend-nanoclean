# NanoClean YOLO Service

Microservicio Python para clasificación de basura usando YOLOv8.

## Requisitos

- Python 3.8+
- CUDA (opcional, para aceleración GPU)

## Instalación

```bash
cd yolo-service
pip install -r requirements.txt
```

## Modelo

1. Entrena el modelo con:
   ```bash
   cd C:\Users\Dennishu\Downloads\entre\archive (1)
   yolo classify train data=nano_dataset/data.yaml model=yolov8n-cls.pt epochs=15
   ```

2. Copia el modelo entrenado a:
   ```
   yolo-service/model/best.pt
   ```

## Ejecutar

```bash
cd yolo-service
uvicorn app:app --host 0.0.0.0 --port 8080
```

## Endpoints

### GET /
Estado del servicio

### GET /health
Verificación de salud

### POST /classify
Clasificar imagen (multipart form)

**Body:** imagen file

**Response:**
```json
{
  "success": true,
  "detection": {
    "class": "organico",
    "confidence": 0.92,
    "class_id": 0
  },
  "contenedor": "ORGANICO",
  "color": "VERDE",
  "instruccion": "Deposite en el contenedor VERDE (orgánico)"
}
```

### POST /classify/base64
Clasificar imagen (base64)

**Body:**
```json
{
  "image": "<base64 encoded image>"
}
```

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| - | - | No requiere variables de entorno |

## Contenedores

| Contenedor | Color | Clase |
|------------|-------|-------|
| ORGANICO | VERDE | organico |
| PAPEL_CARTON | GRIS | papel_carton |
| PLASTICO | AZUL | plastico |
