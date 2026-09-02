import { useEffect, useRef, useState } from "react";
import * as faceapi from "@vladmandic/face-api";

const MODEL_URL = "/models";

function stopStream(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

function eyeRatio(points) {
  const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  return (
    (distance(points[1], points[5]) + distance(points[2], points[4])) /
    (2 * distance(points[0], points[3]))
  );
}

// Shared front-camera + face-api.js descriptor capture, used by both the
// student check-in flow and admin face enrolment. Pass enabled=false to
// keep the camera off until the caller is ready for it.
export function useFaceCapture(enabled = true) {
  const video = useRef(null),
    stream = useRef(null),
    animation = useRef(null);
  const [descriptor, setDescriptor] = useState(null),
    [blinked, setBlinked] = useState(false),
    [message, setMessage] = useState("Loading face verification…");

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    async function start() {
      try {
        await Promise.all([
          faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
          faceapi.nets.faceLandmark68TinyNet.loadFromUri(MODEL_URL),
          faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
        ]);
        stream.current = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: { ideal: 640 } },
          audio: false,
        });
        if (!active) return stopStream(stream.current);
        video.current.srcObject = stream.current;
        setMessage("Center your face, then blink once.");
        const detect = async () => {
          if (!active || !video.current) return;
          try {
            console.log(
              "[faceCapture] detecting — video readyState=",
              video.current.readyState,
              "size=",
              video.current.videoWidth,
              "x",
              video.current.videoHeight,
            );
            const result = await Promise.race([
              faceapi
                .detectSingleFace(
                  video.current,
                  new faceapi.TinyFaceDetectorOptions(),
                )
                .withFaceLandmarks(true)
                .withFaceDescriptor(),
              new Promise((_, reject) =>
                setTimeout(
                  () => reject(new Error("detection timed out after 6s")),
                  6000,
                ),
              ),
            ]);
            console.log("[faceCapture] result:", result);
            if (result) {
              const ratio =
                (eyeRatio(result.landmarks.getLeftEye()) +
                  eyeRatio(result.landmarks.getRightEye())) /
                2;
              if (ratio < 0.2) setBlinked(true);
              setDescriptor(Array.from(result.descriptor));
              setMessage(
                ratio < 0.2
                  ? "Blink detected. Hold still."
                  : "Face detected. Blink once to prove liveness.",
              );
            } else
              setMessage(
                "No face detected. Move into the frame and improve the lighting.",
              );
          } catch (frameError) {
            // A single detection pass can throw transiently (e.g. the video hasn't
            // produced its first frame yet) — retry on the next frame instead of
            // letting the whole loop die silently.
            console.error("face detection frame failed:", frameError);
            setMessage(`Detection error: ${frameError?.message || frameError}`);
          } finally {
            if (active) animation.current = requestAnimationFrame(detect);
          }
        };
        detect();
      } catch (cause) {
        setMessage(
          cause?.name === "NotAllowedError"
            ? "Camera permission was denied. Allow camera access and try again."
            : "Camera or face models could not start on this device.",
        );
      }
    }
    start();
    return () => {
      active = false;
      cancelAnimationFrame(animation.current);
      stopStream(stream.current);
    };
  }, [enabled]);

  return { videoRef: video, descriptor, blinked, message };
}
