export type CameraClock = {
  now: () => number;
  frame: (callback: FrameRequestCallback) => number;
  cancelFrame: (id: number) => void;
  timeout: (callback: () => void, delay: number) => number;
  clearTimeout: (id: number) => void;
};

type CameraCallbacks = {
  onStarted: () => void;
  onEnded: () => void;
  onMode: (mode: "native" | "seek") => void;
  onUnavailable: () => void;
};

/** The camera still moves when an embedded/mobile browser rejects play(). */
export function startCamera(video: HTMLVideoElement, callbacks: CameraCallbacks, clock: CameraClock = {
  now: () => performance.now(), frame: callback => requestAnimationFrame(callback),
  cancelFrame: id => cancelAnimationFrame(id), timeout: (callback, delay) => window.setTimeout(callback, delay),
  clearTimeout: id => window.clearTimeout(id),
}, startAt = 0) {
  let active = true;
  let started = false;
  let finished = false;
  let mode: "native" | "seek" = "native";
  let frame = 0;
  let origin = 0;
  const step = 1 / 24;
  const markStarted = () => { if (active && !started) { started = true; callbacks.onStarted(); } };
  const finish = () => { if (active && !finished) { finished = true; clock.cancelFrame(frame); callbacks.onEnded(); } };
  const unavailable = () => { if (active && !finished) { finished = true; clock.cancelFrame(frame); callbacks.onUnavailable(); } };
  const schedule = () => { if (active && !finished) frame = clock.frame(tick); };
  function tick() {
    if (!active || finished || mode !== "seek") return;
    const elapsed = (clock.now() - origin) / 1000;
    if (!started && elapsed - startAt > 6.5) { unavailable(); return; }
    if (video.readyState >= 1 && !video.seeking) {
      const end = Number.isFinite(video.duration) && video.duration > 0 ? Math.max(0, video.duration - step) : 4 - step;
      const goal = Math.min(end, Math.floor(elapsed / step) * step);
      if (Math.abs(video.currentTime - goal) >= step / 2) {
        try { video.currentTime = goal; } catch { unavailable(); return; }
      } else if (goal >= end - step / 2) { markStarted(); finish(); return; }
    }
    schedule();
  }
  function seekPlayback() {
    if (!active || finished || mode === "seek") return;
    mode = "seek";
    video.pause();
    origin = clock.now() - Math.max(startAt, video.currentTime) * 1000;
    callbacks.onMode(mode);
    schedule();
  }
  const playing = () => { if (mode === "native") markStarted(); };
  const seeked = () => { if (mode === "seek" && video.currentTime > 0) markStarted(); };
  video.muted = true;
  video.playbackRate = 1;
  video.defaultMuted = true;
  video.playsInline = true;
  video.setAttribute("muted", "");
  video.setAttribute("playsinline", "");
  video.setAttribute("webkit-playsinline", "");
  video.addEventListener("playing", playing);
  video.addEventListener("seeked", seeked);
  video.addEventListener("ended", finish);
  video.addEventListener("error", unavailable);
  callbacks.onMode(mode);
  // Resuming an already running shared player does not fire another `playing` event.
  if (!video.paused && video.readyState >= 2) markStarted();
  // A fulfilled play promise does not prove that frames have started moving.
  const watchdog = clock.timeout(() => { if (video.currentTime < startAt + .05) seekPlayback(); }, 450);
  try {
    if (video.readyState >= 1 && Math.abs(video.currentTime - startAt) > step / 2) video.currentTime = startAt;
    void Promise.resolve(video.play()).catch(seekPlayback);
  } catch { seekPlayback(); }
  return () => {
    active = false;
    clock.cancelFrame(frame);
    clock.clearTimeout(watchdog);
    video.removeEventListener("playing", playing);
    video.removeEventListener("seeked", seeked);
    video.removeEventListener("ended", finish);
    video.removeEventListener("error", unavailable);
    video.pause();
  };
}
