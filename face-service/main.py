import math
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="SmartAttend Face Service", version="0.1.0")
THRESHOLD = float(os.getenv("FACE_DISTANCE_THRESHOLD", "0.6"))


class FaceVerification(BaseModel):
    enrolled_embedding: list[float] = Field(min_length=128, max_length=128)
    captured_embedding: list[float] = Field(min_length=128, max_length=128)
    liveness_passed: bool


def euclidean_distance(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions must match")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


@app.get("/health")
def health():
    return {"status": "ok", "threshold": THRESHOLD}


@app.post("/verify")
def verify(payload: FaceVerification):
    if not payload.liveness_passed:
        raise HTTPException(422, "Liveness check failed. Blink and turn toward the camera.")
    distance = euclidean_distance(payload.enrolled_embedding, payload.captured_embedding)
    return {"matched": distance < THRESHOLD, "distance": distance, "score": max(0.0, 1 - distance), "threshold": THRESHOLD}

