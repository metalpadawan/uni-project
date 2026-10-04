import base64
import os
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="SmartAttend Face Service", version="0.2.0")

# SFace's documented NORM_L2 distance threshold (github.com/opencv/opencv_zoo) — not the
# face-api.js-tuned 0.6 this used to default to; that value has no meaning for this model.
THRESHOLD = float(os.getenv("FACE_DISTANCE_THRESHOLD", "1.128"))
# Mean pixel difference (0-255 scale) two captured frames must clear to be treated as a live
# capture rather than the same static photo submitted twice. Not empirically tuned against
# real webcam captures yet — a reasonable starting point, expect to revisit.
MIN_FRAME_DIFFERENCE = float(os.getenv("FACE_MIN_FRAME_DIFFERENCE", "6.0"))

MODEL_DIR = Path(os.getenv("FACE_MODEL_DIR", "models"))
YUNET_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_PATH = MODEL_DIR / "face_recognition_sface_2021dec.onnx"
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"


def ensure_model(path: Path, url: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, path)


ensure_model(YUNET_PATH, YUNET_URL)
ensure_model(SFACE_PATH, SFACE_URL)

detector = cv2.FaceDetectorYN_create(str(YUNET_PATH), "", (320, 320), score_threshold=0.6)
recognizer = cv2.FaceRecognizerSF_create(str(SFACE_PATH), "")


def decode_image(data: str) -> np.ndarray:
    raw = data.split(",", 1)[-1]  # tolerate a data: URL prefix
    try:
        buffer = np.frombuffer(base64.b64decode(raw), dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    except Exception:
        image = None
    if image is None:
        raise ValueError("Could not decode image")
    return image


def detect_largest_face(image: np.ndarray):
    height, width = image.shape[:2]
    detector.setInputSize((width, height))
    _, faces = detector.detect(image)
    if faces is None or len(faces) == 0:
        return None
    return max(faces, key=lambda face: face[-1])


def embed(image: np.ndarray) -> np.ndarray | None:
    face = detect_largest_face(image)
    if face is None:
        return None
    aligned = recognizer.alignCrop(image, face)
    return recognizer.feature(aligned)


class EnrollRequest(BaseModel):
    photo: str


class EnrollResponse(BaseModel):
    embedding: list[float] = Field(min_length=128, max_length=128)


class VerifyRequest(BaseModel):
    enrolled_embedding: list[float] = Field(min_length=128, max_length=128)
    frame_a: str
    frame_b: str


class VerifyResponse(BaseModel):
    matched: bool
    live: bool
    distance: float
    score: float


@app.get("/health")
def health():
    return {"status": "ok", "threshold": THRESHOLD}


@app.post("/enroll", response_model=EnrollResponse)
def enroll(payload: EnrollRequest):
    try:
        image = decode_image(payload.photo)
    except ValueError:
        raise HTTPException(422, "The submitted photo could not be read.")
    embedding = embed(image)
    if embedding is None:
        raise HTTPException(422, "No face was detected in the photo. Center your face and try again.")
    return EnrollResponse(embedding=embedding.flatten().tolist())


@app.post("/verify", response_model=VerifyResponse)
def verify(payload: VerifyRequest):
    try:
        image_a = decode_image(payload.frame_a)
        image_b = decode_image(payload.frame_b)
    except ValueError:
        raise HTTPException(422, "One of the submitted frames could not be read.")

    embedding_a = embed(image_a)
    embedding_b = embed(image_b)
    if embedding_a is None or embedding_b is None:
        return VerifyResponse(matched=False, live=False, distance=999.0, score=0.0)

    resized_a = cv2.resize(image_a, (160, 160))
    resized_b = cv2.resize(image_b, (160, 160))
    frame_difference = float(np.mean(cv2.absdiff(resized_a, resized_b)))
    live = frame_difference >= MIN_FRAME_DIFFERENCE

    enrolled = np.array(payload.enrolled_embedding, dtype=np.float32).reshape(1, -1)
    distance_a = float(recognizer.match(enrolled, embedding_a, cv2.FaceRecognizerSF_FR_NORM_L2))
    distance_b = float(recognizer.match(enrolled, embedding_b, cv2.FaceRecognizerSF_FR_NORM_L2))
    distance = max(distance_a, distance_b)  # both frames must match, not just the easier one
    matched = live and distance < THRESHOLD
    score = max(0.0, 1 - distance / THRESHOLD)
    return VerifyResponse(matched=matched, live=live, distance=distance, score=score)
