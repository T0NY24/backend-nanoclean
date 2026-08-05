import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from model_loader import get_model, is_model_ready
from config import MIN_BBOX_AREA

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

CONFIDENCE_THRESHOLD = 0.10

def classify_image(image_bytes: bytes) -> dict:
    if not is_model_ready():
        return {
            "success": False,
            "error": "Modelo no cargado"
        }

    try:
        import torch
        model = get_model()
        pil_image = Image.open(BytesIO(image_bytes)).convert("RGB")

        # Inferencia con YOLO-World (detecta y ubica el objeto automáticamente)
        results = model.predict(pil_image, conf=CONFIDENCE_THRESHOLD, verbose=False)

        if not results or len(results[0].boxes) == 0:
            return {
                "success": False,
                "error": "No se detectó ningún objeto con suficiente confianza"
            }

        # Tomar la caja con mayor confianza
        boxes = results[0].boxes
        
        # Simulación de profundidad: Filtrar objetos que están muy lejos (área pequeña)
        xyxy = boxes.xyxy
        areas = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
        valid_indices = torch.where(areas >= MIN_BBOX_AREA)[0]
        
        if len(valid_indices) == 0:
            return {
                "success": False,
                "error": "Se detectaron objetos, pero están demasiado lejos (área insuficiente)"
            }

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
            return {
                "success": False,
                "error": f"Se detectó '{raw_class_name}' pero se ignora (no pertenece a papel/plástico/orgánico)"
            }

        class_name = CLASS_MAPPING[raw_class_name]

        # DEBUG: Guardar el frame con el bounding box dibujado
        try:
            import os
            import time
            os.makedirs("debug_frames", exist_ok=True)
            filename = f"debug_frames/manual_{class_name}_{confidence*100:.1f}_{int(time.time())}.jpg"
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(cv_image, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(cv_image, f"{class_name} {confidence:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.imwrite(filename, cv_image)
        except Exception as e:
            print("Error guardando debug frame:", e)

        mapping = CONTAINER_MAPPING.get(class_name, {
            "contenedor": "DESCONOCIDO",
            "color": "N/A",
            "instruccion": "No se pudo clasificar el objeto"
        })

        return {
            "success": True,
            "detection": {
                "class": class_name,
                "confidence": confidence,
                "class_id": class_id,
                "bbox": bbox
            },
            "contenedor": mapping["contenedor"],
            "color": mapping["color"],
            "instruccion": mapping["instruccion"]
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error durante la inferencia: {str(e)}"
        }
