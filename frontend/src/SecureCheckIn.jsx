import { useEffect, useRef, useState } from "react";
import { BrowserQRCodeReader } from "@zxing/browser";
import { Camera, Check, QrCode } from "lucide-react";
import { useFaceCapture } from "./useFaceCapture";

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
  const { videoRef: faceVideo, captured, message: faceMessage, capturing, capture } =
    useFaceCapture(stage === "face", { frames: 2, gapMs: 1000 });
  const qrVideo = useRef(null);
  const scannerControls = useRef(null);
  const [qrMessage, setQrMessage] = useState("");
  const [token, setToken] = useState("");

  useEffect(() => () => scannerControls.current?.stop(), []);

  async function startQr() {
    setToken("");
    setQrMessage("Point the rear camera at the lecturer's rotating QR code.");
    scannerControls.current?.stop();
    scannerControls.current = null;
    try {
      if (!qrVideo.current) return;
      const reader = new BrowserQRCodeReader();
      scannerControls.current = await reader.decodeFromConstraints(
        { video: { facingMode: { ideal: "environment" } }, audio: false },
        qrVideo.current,
        (result) => {
          if (!result) return;
          setToken(tokenFromQr(result.getText()));
          setQrMessage("QR code captured. Continue to live face capture.");
          scannerControls.current?.stop();
          scannerControls.current = null;
        },
      );
    } catch {
      setQrMessage("Camera could not start. Allow camera access, then restart the scanner.");
    }
  }

  useEffect(() => {
    if (stage === "qr") startQr();
  }, [stage]);

  function beginFace() {
    scannerControls.current?.stop();
    scannerControls.current = null;
    setStage("face");
  }

  const message = stage === "face" ? faceMessage : qrMessage;
  const facesReady = captured.length === 2;

  return (
    <div className="secure-capture">
      <div className="capture-progress" aria-label={`Check-in step ${stage === "qr" ? 1 : 2} of 2`}>
        <span className={stage === "face" ? "complete" : ""}>{stage === "face" ? <Check /> : <QrCode />}</span>
        <i />
        <span className={stage === "face" ? "complete" : ""}><Camera /></span>
      </div>
      <small>STEP {stage === "qr" ? "1" : "2"} OF 2</small>
      <h2 id="modal-title">{stage === "qr" ? `Scan ${course?.course_code || "class"} QR code` : "Verify your live face"}</h2>
      <div className={`camera-frame ${stage === "qr" ? "qr-camera" : "face-camera"}`}>
        <video ref={stage === "qr" ? qrVideo : faceVideo} autoPlay muted playsInline aria-label={stage === "qr" ? "Rear camera QR scanner" : "Front camera face preview"} />
        <div className={stage === "qr" ? "qr-guide" : "face-guide"} />
      </div>
      <p className="capture-message" role="status">{message}</p>
      {error && <p className="inline-error" role="alert">{error}</p>}
      {stage === "qr" ? (
        <>
          {!token && <button className="outline full" onClick={startQr}>Restart scanner</button>}
          <button className="primary full" disabled={!token} onClick={beginFace}>Continue to face capture <Camera size={17} /></button>
        </>
      ) : facesReady ? (
        <button className="primary full" disabled={busy} onClick={() => onComplete({ frameA: captured[0], frameB: captured[1], token })}>
          {busy ? "Verifying attendance..." : "Verify face and mark present"} <Check size={17} />
        </button>
      ) : (
        <button className="primary full" disabled={capturing} onClick={capture}>{capturing ? "Capturing..." : "Capture face"} <Camera size={17} /></button>
      )}
    </div>
  );
}
