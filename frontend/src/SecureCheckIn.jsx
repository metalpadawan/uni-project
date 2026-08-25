import { useEffect, useRef, useState } from "react";
import * as faceapi from "@vladmandic/face-api";
import { Camera, Check, QrCode } from "lucide-react";

const MODEL_URL = "/models";

function stop(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

function eyeRatio(points) {
  const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
  return (
    (distance(points[1], points[5]) + distance(points[2], points[4])) /
    (2 * distance(points[0], points[3]))
  );
}

export default function SecureCheckIn({ course, busy, error, onComplete }) {
  const video = useRef(null),
    stream = useRef(null),
    animation = useRef(null);
  const [stage, setStage] = useState("face"),
    [message, setMessage] = useState("Loading face verification…");
  const [descriptor, setDescriptor] = useState(null),
    [blinked, setBlinked] = useState(false),
    [token, setToken] = useState("");

  useEffect(() => {
    let active = true;
    async function startFace() {
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
        if (!active) return stop(stream.current);
        video.current.srcObject = stream.current;
        setMessage("Center your face, then blink once.");
        const detect = async () => {
          if (!active || !video.current) return;
          const result = await faceapi
            .detectSingleFace(
              video.current,
              new faceapi.TinyFaceDetectorOptions(),
            )
            .withFaceLandmarks(true)
            .withFaceDescriptor();
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
          animation.current = requestAnimationFrame(detect);
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
    startFace();
    return () => {
      active = false;
      cancelAnimationFrame(animation.current);
      stop(stream.current);
    };
  }, []);

  async function beginQr() {
    cancelAnimationFrame(animation.current);
    stop(stream.current);
    setStage("qr");
    setMessage("Point the rear camera at the lecturer’s rotating QR code.");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      video.current.srcObject = stream.current;
      if ("BarcodeDetector" in window) {
        const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
        const scan = async () => {
          if (!video.current || video.current.readyState < 2)
            return (animation.current = requestAnimationFrame(scan));
          const codes = await detector.detect(video.current).catch(() => []);
          if (codes[0]?.rawValue) {
            setToken(codes[0].rawValue);
            setMessage("QR code captured. Ready to verify both checks.");
            stop(stream.current);
            return;
          }
          animation.current = requestAnimationFrame(scan);
        };
        scan();
      } else
        setMessage(
          "Automatic QR scanning is unavailable in this browser. Paste the QR token below.",
        );
    } catch {
      setMessage("Rear camera could not start. Paste the QR token below.");
    }
  }

  return (
    <div className="secure-capture">
      <div
        className="capture-progress"
        aria-label={`Check-in step ${stage === "face" ? 1 : 2} of 2`}
      >
        <span className="complete">
          <Check />
        </span>
        <i />
        <span className={stage === "qr" ? "complete" : ""}>
          {stage === "qr" ? <QrCode /> : <Camera />}
        </span>
      </div>
      <small>STEP {stage === "face" ? "1" : "2"} OF 2</small>
      <h2 id="modal-title">
        {stage === "face"
          ? "Verify your live face"
          : `Scan ${course?.course_code || "class"} QR code`}
      </h2>
      <div className="camera-frame">
        <video
          ref={video}
          autoPlay
          muted
          playsInline
          aria-label={
            stage === "face"
              ? "Front camera face preview"
              : "Rear camera QR scanner"
          }
        />
        <div className={stage === "face" ? "face-guide" : "qr-guide"} />
      </div>
      <p className="capture-message" role="status">
        {message}
      </p>
      {stage === "qr" && (
        <label className="token-fallback">
          QR token
          <input
            value={token}
            onChange={(event) => setToken(event.target.value.trim())}
            autoComplete="off"
            placeholder="Scan automatically or paste token"
          />
        </label>
      )}
      {error && (
        <p className="inline-error" role="alert">
          {error}
        </p>
      )}
      {stage === "face" ? (
        <button
          className="primary full"
          disabled={!descriptor || !blinked}
          onClick={beginQr}
        >
          Continue after blink <QrCode size={17} />
        </button>
      ) : (
        <button
          className="primary full"
          disabled={!token || busy}
          onClick={() =>
            onComplete({ embedding: descriptor, token, liveness: blinked })
          }
        >
          {busy ? "Verifying both checks…" : "Verify face + QR"}{" "}
          <Check size={17} />
        </button>
      )}
    </div>
  );
}
