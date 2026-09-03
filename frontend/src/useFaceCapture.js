import { useEffect, useRef, useState } from "react";

function stopStream(stream) {
  stream?.getTracks().forEach((track) => track.stop());
}

// Shared front-camera capture used by check-in (two frames, a beat apart) and
// enrollment/registration (one photo). All face detection and recognition now
// happens server-side (face-service) — this hook only owns the camera, a short
// countdown, and grabbing JPEG frame(s) off the <video> via a <canvas>. No
// client-side ML inference happens here at all.
export function useFaceCapture(enabled = true, { frames = 1, gapMs = 1200 } = {}) {
  const video = useRef(null),
    stream = useRef(null),
    canvas = useRef(null);
  const [captured, setCaptured] = useState([]),
    [message, setMessage] = useState("Loading camera…"),
    [capturing, setCapturing] = useState(false);

  if (!canvas.current && typeof document !== "undefined") {
    canvas.current = document.createElement("canvas");
  }

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    setCaptured([]);
    (async () => {
      try {
        stream.current = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: { ideal: 640 } },
          audio: false,
        });
        if (!active) return stopStream(stream.current);
        video.current.srcObject = stream.current;
        setMessage("Center your face in the frame, then hold still.");
      } catch (cause) {
        setMessage(
          cause?.name === "NotAllowedError"
            ? "Camera permission was denied. Allow camera access and try again."
            : "Camera could not start on this device.",
        );
      }
    })();
    return () => {
      active = false;
      stopStream(stream.current);
    };
  }, [enabled]);

  function grabFrame() {
    const el = canvas.current;
    el.width = video.current.videoWidth;
    el.height = video.current.videoHeight;
    el.getContext("2d").drawImage(video.current, 0, 0);
    return el.toDataURL("image/jpeg", 0.85);
  }

  async function capture() {
    if (capturing || !video.current) return;
    setCapturing(true);
    setCaptured([]);
    const shots = [];
    for (let i = 0; i < frames; i++) {
      for (let s = 3; s > 0; s--) {
        setMessage(`Hold still — capturing in ${s}…`);
        await new Promise((resolve) => setTimeout(resolve, 700));
      }
      shots.push(grabFrame());
      setCaptured([...shots]);
      const remaining = frames - shots.length;
      if (remaining > 0) {
        setMessage("Got it. One more…");
        await new Promise((resolve) => setTimeout(resolve, gapMs));
      } else {
        setMessage("Captured.");
      }
    }
    setCapturing(false);
  }

  return { videoRef: video, captured, message, capturing, capture };
}
