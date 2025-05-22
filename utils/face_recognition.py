import os
import cv2
from insightface.app import FaceAnalysis
import numpy as np
from ultralytics import YOLO

model = YOLO(r"models\face_detector.pt")
app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider'])
app.prepare(ctx_id=0)

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def load_embeddings(folder, valid_student_ids):
    embeddings = {}
    for sid in valid_student_ids:
        emb_path = os.path.join(folder, f"{sid}.npy")
        if os.path.exists(emb_path):
            emb = np.load(emb_path)
            emb = emb / np.linalg.norm(emb)
            embeddings[sid] = emb
    return embeddings

def read_image(image_input):
    if isinstance(image_input, str):
        img = cv2.imread(image_input)
        if img is None:
            print(f"Error: Image at path '{image_input}' could not be read.")
        return img
    elif isinstance(image_input, np.ndarray):
        return image_input
    else:
        print("Invalid input: Must be a file path or NumPy array.")
        return None

def detect_face(image_input, max_det=None):
    img = read_image(image_input)
    if img is None:
        return None
    faces = []
    img_h, img_w = img.shape[:2]
    
    if max_det:
        results = model(img, verbose=False, max_det=max_det, device='cuda')
    else:
        results = model(img, verbose=False, device='cuda')
    if not results or results[0].boxes is None or len(results[0].boxes.xyxy) == 0:
        return faces

    for box in results[0].boxes.xyxy:
        x1, y1, x2, y2 = map(int, box)
        pad_w = int(0.5 * (x2 - x1))
        pad_h = int(0.5 * (y2 - y1))

        x1 = max(0, x1 - pad_w)
        y1 = max(0, y1 - pad_h)
        x2 = min(img_w, x2 + pad_w)
        y2 = min(img_h, y2 + pad_h)

        face = img[y1:y2, x1:x2]
        faces.append((face, (x1, y1, x2, y2)))

    return faces

def get_embedding(image_input):
    face = read_image(image_input)
    if face is None:
        return None
    faces = app.get(face)
    if len(faces) == 0:
        return None
    return faces[0].embedding