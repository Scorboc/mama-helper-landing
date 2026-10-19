import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { isRoomLocation } from "@/lib/room-experience";
import { startCamera } from "@/lib/room-handoff";
import { useRoomVideo } from "@/lib/room-media";

/** One persistent camera layer and one opacity for the entire arriving interface. */
export default function RoomTransition() {
  const location = useLocation();
  const video = useRoomVideo();
  const cancelCamera = useRef<(() => void) | null>(null);
  const cameraEnded = useRef(false);
  const fadeEnded = useRef(false);
  const fadeDuration = useRef(2400);
  const [prepared, setPrepared] = useState(false);
  const [phase, setPhase] = useState<"idle" | "holding" | "moving">("idle");
  const [playing, setPlaying] = useState(false);
  const [revealing, setRevealing] = useState(false);
  const [playback, setPlayback] = useState<"native" | "seek">("native");
  const complete = useCallback(() => {
    document.documentElement.dataset.roomTransition = "complete";
    document.documentElement.dataset.roomCamera = "still";
    document.documentElement.style.removeProperty("--room-interface-opacity");
    cancelCamera.current?.(); cancelCamera.current = null;
    setPhase("idle"); setRevealing(false);
  }, []);
  useEffect(() => {
    const prepare = () => setPrepared(true);
    const start = (event: Event) => {
      const moving = !!(event as CustomEvent<{ moving?: boolean }>).detail?.moving;
      const startAt = (event as CustomEvent<{ startAt?: number }>).detail?.startAt || 0;
      cancelCamera.current?.(); cancelCamera.current = null;
      cameraEnded.current = !moving;
      fadeEnded.current = false;
      fadeDuration.current = !moving && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 260 : 2400;
      document.documentElement.dataset.roomTransition = "holding";
      document.documentElement.dataset.roomCamera = moving ? "moving" : "still";
      document.documentElement.style.setProperty("--room-interface-opacity", "0");
      setRevealing(false); setPlaying(false);
      if (moving && video.current) {
        setPhase("moving");
        cancelCamera.current = startCamera(video.current, {
          onStarted: () => setPlaying(true), onMode: setPlayback,
          onEnded: () => { cameraEnded.current = true; if (fadeEnded.current) complete(); },
          onUnavailable: () => { cameraEnded.current = true; setPhase("holding"); if (fadeEnded.current) complete(); },
        }, undefined, startAt);
      } else { cameraEnded.current = true; setPhase("holding"); }
    };
    window.addEventListener("mama:room-prepare-outro", prepare);
    const hide = () => setPrepared(false);
    window.addEventListener("mama:room-hide-journey", hide);
    window.addEventListener("mama:room-exit", start);
    return () => {
      window.removeEventListener("mama:room-prepare-outro", prepare);
      window.removeEventListener("mama:room-hide-journey", hide);
      window.removeEventListener("mama:room-exit", start);
      cancelCamera.current?.();
      delete document.documentElement.dataset.roomTransition;
      delete document.documentElement.dataset.roomCamera;
      document.documentElement.style.removeProperty("--room-interface-opacity");
    };
  }, [complete, video]);
  useEffect(() => {
    if (location.pathname !== "/" && isRoomLocation(location.search, location.pathname)) return;
    // The guest welcome is also an arriving interface; preserve its live final shot.
    if (location.pathname === "/" && new URLSearchParams(location.search).get("intro") !== "1" && document.documentElement.dataset.roomTransition) return;
    cancelCamera.current?.(); cancelCamera.current = null;
    setPhase("idle"); setRevealing(false);
    delete document.documentElement.dataset.roomTransition;
    delete document.documentElement.dataset.roomCamera;
    document.documentElement.style.removeProperty("--room-interface-opacity");
  }, [location.pathname, location.search]);
  useEffect(() => {
    if (phase === "idle") return;
    const reveal = () => setRevealing(true);
    const check = () => {
      if ((phase === "holding" || playing) && document.querySelector('.room-surface[data-room-ready="true"], .room-guest')) reveal();
    };
    const observer = new MutationObserver(check);
    observer.observe(document.getElementById("root")!, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-room-ready"] });
    check();
    // Slow media must never leave the account, retry or urgent-help controls invisible.
    const deadline = window.setTimeout(reveal, 1600);
    return () => { observer.disconnect(); window.clearTimeout(deadline); };
  }, [phase, playing]);
  useEffect(() => {
    if (!revealing) return;
    document.documentElement.dataset.roomTransition = "revealing";
    const origin = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, Math.max(0, (now - origin) / fadeDuration.current));
      document.documentElement.style.setProperty("--room-interface-opacity", String(progress));
      if (progress < 1) frame = requestAnimationFrame(tick);
      else { fadeEnded.current = true; if (cameraEnded.current) complete(); }
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [revealing, complete]);
  const walking = prepared && location.pathname === "/" && new URLSearchParams(location.search).get("intro") === "1";
  return <div className={phase === "idle" ? (walking ? "room-journey-active" : "room-outro-preload") : `room-handoff ${phase}`} data-room-reveal={revealing} data-room-playback={playback} aria-hidden="true">
    <div className="room-ambient" />
    <div className="room-film">
      <img className="room-still" src={walking ? "/media/room/start-v12.webp" : "/media/room/rest-v12.webp"} alt="" />
      <video data-room-journey ref={video} src="/media/room/journey-v13-seek.mp4" poster="/media/room/start-v12.webp" muted playsInline preload={prepared ? "auto" : "none"} disablePictureInPicture />
    </div>
  </div>;
}
