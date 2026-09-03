import base64

import cv2
import numpy as np
import pytest

from main import VerifyRequest, decode_image, detect_largest_face, embed, verify


def encode(image: np.ndarray) -> str:
    ok, buffer = cv2.imencode(".jpg", image)
    assert ok
    return base64.b64encode(buffer.tobytes()).decode()


def test_decode_image_rejects_garbage():
    with pytest.raises(ValueError):
        decode_image("not-valid-image-data")


def test_no_face_found_in_a_blank_image():
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    assert detect_largest_face(blank) is None
    assert embed(blank) is None


def test_verify_reports_no_match_when_no_face_is_present():
    blank = encode(np.zeros((200, 200, 3), dtype=np.uint8))
    result = verify(VerifyRequest(enrolled_embedding=[0.1] * 128, frame_a=blank, frame_b=blank))
    assert result.matched is False
    assert result.live is False


def test_verify_rejects_two_identical_frames_as_not_live():
    # Even if a face were detected, submitting the exact same frame twice must never
    # pass the liveness check — that's the core anti-replay guarantee of this endpoint.
    frame = encode(np.full((200, 200, 3), 128, dtype=np.uint8))
    result = verify(VerifyRequest(enrolled_embedding=[0.1] * 128, frame_a=frame, frame_b=frame))
    assert result.live is False
    assert result.matched is False
