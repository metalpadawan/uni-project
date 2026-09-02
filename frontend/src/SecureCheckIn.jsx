import { useEffect, useRef, useState } from "react";
import { Camera, Check, QrCode } from "lucide-react";
import { useFaceCapture } from "./useFaceCapture";

function stop(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

export default function SecureCheckIn({ course, busy, error, onComplete }) {
  const [stage, setStage] = useState("face");
  const {
    videoRef: faceVideo,
    descriptor,
    blinked,
    message: faceMessage,
  } = useFaceCapture(stage === "face");
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

  async function beginQr() {
    setStage("qr");
    setQrMessage("Point the rear camera at the lecturer’s rotating QR code.");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      qrVideo.current.srcObject = stream.current;
      if ("BarcodeDetector" in window) {
        const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
        const scan = async () => {
          if (!qrVideo.current || qrVideo.current.readyState < 2)
            return (animation.current = requestAnimationFrame(scan));
          const codes = await detector.detect(qrVideo.current).catch(() => []);
          if (codes[0]?.rawValue) {
            setToken(codes[0].rawValue);
            setQrMessage("QR code captured. Ready to verify both checks.");
            stop(stream.current);
            return;
          }
          animation.current = requestAnimationFrame(scan);
        };
        scan();
      } else
        setQrMessage(
          "Automatic QR scanning is unavailable in this browser. Paste the QR token below.",
        );
    } catch {
      setQrMessage("Rear camera could not start. Paste the QR token below.");
    }
  }

  const message = stage === "face" ? faceMessage : qrMessage;

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
          ref={stage === "face" ? faceVideo : qrVideo}
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
