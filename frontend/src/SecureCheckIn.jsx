import { useEffect, useRef, useState } from "react";
import { Camera, Check, QrCode } from "lucide-react";
import { useFaceCapture } from "./useFaceCapture";

function stop(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

function tokenFromQr(value) {
  try {
    const url = new URL(value);
    return url.searchParams.get("qr") || value;
  } catch {
    return value;
  }
}

export default function SecureCheckIn({ course, busy, error, onComplete }) {
  const [stage, setStage] = useState("qr");
  const {
    videoRef: faceVideo,
    captured,
    message: faceMessage,
    capturing,
    capture,
  } = useFaceCapture(stage === "face", { frames: 2, gapMs: 1000 });
  const qrVideo = useRef(null),
    stream = useRef(null),
    animation = useRef(null);
  const [qrMessage, setQrMessage] = useState("");
  const [token, setToken] = useState("");

  useEffect(
    () => () => {
      cancelAnimationFrame(animation.current);
      stop(stream.current);
    },
    [],
  );

  async function startQr() {
    setQrMessage("Point the rear camera at the lecturer’s rotating QR code.");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      if (!qrVideo.current) return stop(stream.current);
      qrVideo.current.srcObject = stream.current;
      if ("BarcodeDetector" in window) {
        const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
        const scan = async () => {
          if (!qrVideo.current || qrVideo.current.readyState < 2)
            return (animation.current = requestAnimationFrame(scan));
          const codes = await detector.detect(qrVideo.current).catch(() => []);
          if (codes[0]?.rawValue) {
            setToken(tokenFromQr(codes[0].rawValue));
            setQrMessage("QR code captured. Continue to live face capture.");
            stop(stream.current);
            return;
          }
          animation.current = requestAnimationFrame(scan);
        };
        scan();
      } else {
        setQrMessage(
          "Automatic QR scanning is unavailable in this browser. Paste the QR token below.",
        );
      }
    } catch {
      setQrMessage("Rear camera could not start. Paste the QR token below.");
    }
  }

  useEffect(() => {
    if (stage === "qr") startQr();
  }, [stage]);

  function beginFace() {
    cancelAnimationFrame(animation.current);
    stop(stream.current);
    setStage("face");
  }

  const message = stage === "face" ? faceMessage : qrMessage;
  const facesReady = captured.length === 2;

  return (
    <div className="secure-capture">
      <div
        className="capture-progress"
        aria-label={`Check-in step ${stage === "qr" ? 1 : 2} of 2`}
      >
        <span className={stage === "face" ? "complete" : ""}>
          {stage === "face" ? <Check /> : <QrCode />}
        </span>
        <i />
        <span className={stage === "face" ? "complete" : ""}>
          <Camera />
        </span>
      </div>
      <small>STEP {stage === "qr" ? "1" : "2"} OF 2</small>
      <h2 id="modal-title">
        {stage === "qr"
          ? `Scan ${course?.course_code || "class"} QR code`
          : "Verify your live face"}
      </h2>
      <div className={`camera-frame ${stage === "qr" ? "qr-camera" : "face-camera"}`}>
        <video
          ref={stage === "qr" ? qrVideo : faceVideo}
          autoPlay
          muted
          playsInline
          aria-label={
            stage === "qr" ? "Rear camera QR scanner" : "Front camera face preview"
          }
        />
        <div className={stage === "qr" ? "qr-guide" : "face-guide"} />
      </div>
      <p className="capture-message" role="status">
        {message}
      </p>
      {stage === "qr" && (
        <label className="token-fallback">
          QR token
          <input
            value={token}
            onChange={(event) => setToken(tokenFromQr(event.target.value.trim()))}
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
      {stage === "qr" ? (
        <button className="primary full" disabled={!token} onClick={beginFace}>
          Continue to face capture <Camera size={17} />
        </button>
      ) : facesReady ? (
        <button
          className="primary full"
          disabled={busy}
          onClick={() => onComplete({ frameA: captured[0], frameB: captured[1], token })}
        >
          {busy ? "Verifying attendance…" : "Verify face and mark present"} <Check size={17} />
        </button>
      ) : (
        <button className="primary full" disabled={capturing} onClick={capture}>
          {capturing ? "Capturing…" : "Capture face"} <Camera size={17} />
        </button>
      )}
    </div>
  );
}
