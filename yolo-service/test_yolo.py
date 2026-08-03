from ultralytics import YOLOWorld
import cv2
from PIL import Image

def test():
    print("Loading YOLO-World...")
    model = YOLOWorld("yolov8s-worldv2.pt")
    
    classes = [
        "cardboard", "paper", "crumpled paper", "crumpled paper ball",
        "plastic bottle", "plastic bag", "plastic container", 
        "organic waste", "food waste", "fruit", "vegetable"
    ]
    model.set_classes(classes)
    
    # Grab a frame from camera to test
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Could not grab frame from camera.")
        return
        
    print("Running prediction...")
    # Save the frame
    cv2.imwrite("test_frame.jpg", frame)
    
    # Predict with a very low threshold
    results = model.predict(frame, conf=0.01, verbose=False)
    
    if not results or len(results[0].boxes) == 0:
        print("Nothing detected even with conf=0.01")
        return
        
    boxes = results[0].boxes
    for i in range(len(boxes)):
        class_id = int(boxes.cls[i].item())
        conf = float(boxes.conf[i].item())
        name = results[0].names[class_id]
        print(f"Detected: {name} | Confidence: {conf:.4f}")

if __name__ == "__main__":
    test()
