import os
import torch
from ultralytics import YOLOWorld

_model = None

def load_model():
    global _model
    if _model is None:
        try:
            print("Cargando modelo YOLO-World (Zero-Shot Object Detection)...")
            _model = YOLOWorld("yolov8s-worldv2.pt")
            
            # Definir clases mucho más amplias para asegurar que atrape cualquier variación
            _model.set_classes([
                "cardboard", "cardboard box", 
                "paper", "crumpled paper", "crumpled piece of paper", "white paper ball", "wad of paper",
                "plastic bottle", "plastic cup", "plastic container",
                "food waste", "fruit", "vegetable", "banana peel", "apple core"
            ])
            print("Modelo YOLO-World cargado exitosamente.")
        except Exception as e:
            print(f"Error cargando YOLO-World: {e}")
            raise e
    return _model

def get_model():
    return load_model()

def is_model_ready():
    return _model is not None

