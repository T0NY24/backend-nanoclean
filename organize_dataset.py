import os
import shutil
import random
from pathlib import Path

# Rutas
SOURCE_DIR = Path(r"C:\Users\Dennishu\Downloads\entre\archive (1)\garbage_classification")
DEST_DIR = Path(r"C:\Users\Dennishu\Downloads\entre\nano_dataset")

# Mapeo de carpetas dataset -> clase YOLO
MAPPING = {
    "biological": "organico",
    "paper": "papel_carton",
    "cardboard": "papel_carton",
    "plastic": "plastico",
}

# Proporción train/val
TRAIN_RATIO = 0.8

def create_dirs():
    """Crear estructura de carpetas"""
    for split in ["train", "val"]:
        for clase in ["organico", "papel_carton", "plastico"]:
            dir_path = DEST_DIR / "images" / split / clase
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"Creado: {dir_path}")
    
    (DEST_DIR / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (DEST_DIR / "labels" / "val").mkdir(parents=True, exist_ok=True)
    print("Carpetas de labels creadas")

def organize_images():
    """Copiar y separar imágenes train/val"""
    
    for source_folder, dest_class in MAPPING.items():
        source_path = SOURCE_DIR / source_folder
        
        if not source_path.exists():
            print(f"⚠️ No existe: {source_path}")
            continue
        
        # Obtener todas las imágenes
        images = [f for f in source_path.iterdir() if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
        print(f"\n{source_folder} -> {dest_class}: {len(images)} imágenes")
        
        # Mezclar aleatoriamente
        random.shuffle(images)
        
        # Separar train/val
        split_idx = int(len(images) * TRAIN_RATIO)
        train_images = images[:split_idx]
        val_images = images[split_idx:]
        
        print(f"  Train: {len(train_images)}, Val: {len(val_images)}")
        
        # Copiar imágenes de train
        for img in train_images:
            dest = DEST_DIR / "images" / "train" / dest_class / img.name
            # Evitar sobreescribir si hay nombres duplicados de diferentes fuentes
            if dest.exists():
                dest = DEST_DIR / "images" / "train" / dest_class / f"{source_folder}_{img.name}"
            shutil.copy2(img, dest)
        
        # Copiar imágenes de val
        for img in val_images:
            dest = DEST_DIR / "images" / "val" / dest_class / img.name
            if dest.exists():
                dest = DEST_DIR / "images" / "val" / dest_class / f"{source_folder}_{img.name}"
            shutil.copy2(img, dest)
    
    print("\n✅ Imágenes organizadas")

def create_data_yaml():
    """Crear archivo data.yaml"""
    
    content = """# NanoClean Dataset Configuration
path: ./nano_dataset
train: images/train
val: images/val

nc: 3

names:
  0: organico
  1: papel_carton
  2: plastico
"""
    
    yaml_path = SOURCE_DIR.parent / "data.yaml"
    with open(yaml_path, 'w') as f:
        f.write(content)
    
    print(f"\n📄 data.yaml creado en: {yaml_path}")

def create_empty_labels():
    """Crear archivos labels vacíos (para estructura YOLO)"""
    # Como no tenemos annotations, creamos labels vacíos
    # O podemos omitir este paso si el entrenamiento no los necesita
    
    for split in ["train", "val"]:
        for clase in ["organico", "papel_carton", "plastico"]:
            labels_dir = DEST_DIR / "labels" / split
            # Solo crear las carpetas, no archivos vacíos
            print(f"Labels dir: {labels_dir}")

def count_final():
    """Contar imágenes finales"""
    print("\n📊 Resumen final:")
    for split in ["train", "val"]:
        print(f"\n{split.upper()}:")
        total = 0
        for clase in ["organico", "papel_carton", "plastico"]:
            count = len(list((DEST_DIR / "images" / split / clase).glob("*")))
            print(f"  {clase}: {count}")
            total += count
        print(f"  TOTAL: {total}")

def main():
    print("🚀 Iniciando organización del dataset NanoClean\n")
    print(f"Origen: {SOURCE_DIR}")
    print(f"Destino: {DEST_DIR}\n")
    
    random.seed(42)  # Reproducibilidad
    
    create_dirs()
    organize_images()
    create_data_yaml()
    count_final()
    
    print("\n✨ ¡Listo! Ahora puedes entrenar con:")
    print("   yolo detect train data=./data.yaml model=yolov8n.pt epochs=15")

if __name__ == "__main__":
    main()
