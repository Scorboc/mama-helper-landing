import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowRight } from "lucide-react";
import { roomCues, ROOM_OUTRO_START } from "@/lib/room-experience";
import { useRoomVideo } from "@/lib/room-media";
import { RoomMotion, ROOM_MAX_SPEED } from "@/lib/room-motion";

/** Native scrolling with a damped release and one uninterrupted automatic final shot. */
export default function RoomIntroduction({ onComplete, returning }: { onComplete: (moving?: boolean, startAt?: number) => void; returning: boolean }) {
  const section = useRef<HTMLElement>(null);
  const video = useRoomVideo();
  const completed = useRef(false);
  const phaseRef = useRef<"scrub" | "outro">("scrub");
  const onCompleteRef = useRef(onComplete);
  const [time, setTime] = useState(0);
  const [progress, setProgress] = useState(0);
  const [failed, setFailed] = useState(false);
  const [reduced, setReduced] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [allowMotion, setAllowMotion] = useState(false);
  const canScrub = !reduced || allowMotion;

  useLayoutEffect(() => { onCompleteRef.current = onComplete; }, [onComplete]);
  function finish() {
    if (completed.current) return;
    completed.current = true;
    video.current?.pause();
    onCompleteRef.current();
  }
  useLayoutEffect(() => {
    // A replay starts at the first frame, even after a long chat page.
    const root = document.documentElement;
    const previousBehavior = root.style.scrollBehavior;
    const previousRestoration = window.history.scrollRestoration;
    root.style.scrollBehavior = "auto";
    window.history.scrollRestoration = "manual";
    window.scrollTo({ top: 0, behavior: "instant" });
    return () => {
      root.style.scrollBehavior = previousBehavior;
      window.history.scrollRestoration = previousRestoration;
    };
  }, []);
  useEffect(() => {
    window.dispatchEvent(new Event(canScrub && !failed ? "mama:room-prepare-outro" : "mama:room-hide-journey"));
  }, [canScrub, failed]);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => { setReduced(media.matches); setAllowMotion(false); };
    media.addEventListener("change", change);
    return () => media.removeEventListener("change", change);
  }, []);
  useEffect(() => {
    const node = video.current;
    const track = section.current;
    if (!node || !track || !canScrub || failed) return;
    let disposed = false, frame = 0, lastTick = 0, seekAt = 0;
    let playBlocked = false, playPending = false, playbackRate = .25, publishedAt = 0;
    let nativeRequestedAt = 0, observedTime = 0;
    let touchY: number | null = null;
    let touchAt = 0, touchSpeed = 0, releaseUntil = 0;
    let wheelAt = -Infinity, wheelRelease = 0;
    let viewportWidth = window.innerWidth;
    let travel = window.innerHeight * 7;
    const motion = new RoomMotion(ROOM_OUTRO_START);
    const frameLength = 1 / 24;
    const root = document.documentElement;
    const previousDistance = track.style.getPropertyValue("--room-scroll-distance");
    track.style.setProperty("--room-scroll-distance", `${travel}px`);
    root.classList.add("room-scrolling");
    phaseRef.current = "scrub";
    node.pause();
    if (node.readyState >= 1) node.currentTime = 0;

    function publish() {
      if (disposed || node!.seeking) return;
      setTime(node!.currentTime);
      setProgress(Math.min(1, node!.currentTime / ROOM_OUTRO_START));
    }
    function schedule() {
      if (!disposed && !frame && phaseRef.current === "scrub") frame = requestAnimationFrame(tick);
    }
    function sync() {
      if (disposed || phaseRef.current !== "scrub") return;
      const distance = Math.min(travel, Math.max(0, -track!.getBoundingClientRect().top));
      motion.scroll(distance / travel * ROOM_OUTRO_START, performance.now());
      schedule();
    }
    function startOutro() {
      if (disposed || completed.current) return;
      phaseRef.current = "outro";
      completed.current = true;
      onCompleteRef.current(true, node!.currentTime);
    }
    function playForward() {
      if (playPending || !node!.paused || playBlocked) return;
      playPending = true;
      if (!nativeRequestedAt) nativeRequestedAt = performance.now();
      try {
        void Promise.resolve(node!.play()).catch((error: unknown) => { if (!disposed && !(error instanceof DOMException && error.name === "AbortError")) playBlocked = true; })
          .finally(() => { playPending = false; if (disposed && phaseRef.current !== "outro") node!.pause(); });
      } catch { playPending = false; playBlocked = true; }
    }
    function wakeDecoder() {
      // Mobile data/energy policies can ignore preload. A real user gesture
      // must be able to start loading and retry playback that a RAF could not.
      if (playBlocked || node!.readyState < 2) {
        playBlocked = false;
        nativeRequestedAt = 0;
        playForward();
        // Priming the decoder must never turn a tap into automatic movement.
        if (motion.target <= node!.currentTime + frameLength / 2) node!.pause();
        schedule();
      }
    }
    function tick(now: number) {
      frame = 0;
      if (disposed || phaseRef.current !== "scrub") return;
      const dt = lastTick ? now - lastTick : 16;
      lastTick = now;
      if ((node!.readyState < 2 && !node!.seeking) || (node!.seeking && now - seekAt > 150)) { schedule(); return; }
      const position = motion.step(dt, now);
      const goal = Math.round(position / frameLength) * frameLength;
      const ahead = motion.target - node!.currentTime;
      if (Math.abs(node!.currentTime - observedTime) > .01) { observedTime = node!.currentTime; nativeRequestedAt = now; }
      if (!playBlocked && nativeRequestedAt && ahead > frameLength / 2 && now - nativeRequestedAt > 550) {
        playBlocked = true; node!.pause(); motion.position = node!.currentTime;
        schedule(); return;
      }
      if (!playBlocked && ahead > frameLength / 2 && !node!.seeking) {
        // Forward gestures use the decoder's continuous playback, not a chain of seeks.
        const desired = Math.max(.25, Math.min(ROOM_MAX_SPEED, ahead / .22));
        playbackRate += (desired - playbackRate) * (1 - Math.exp(-Math.min(40, dt) / 110));
        node!.playbackRate = playbackRate;
        playForward();
      } else {
        node!.pause(); playbackRate = .25; nativeRequestedAt = 0;
        if (!node!.seeking && Math.abs(goal - node!.currentTime) > frameLength / 2 && (playBlocked || ahead < -frameLength / 2)) {
          seekAt = now;
          node!.currentTime = Math.max(0, Math.min(ROOM_OUTRO_START, goal));
        }
      }
      if (!node!.seeking && motion.target >= ROOM_OUTRO_START - frameLength / 2 && node!.currentTime >= ROOM_OUTRO_START - 3 * frameLength) { startOutro(); return; }
      if (now - publishedAt > 40) { publish(); publishedAt = now; }
      if (motion.moving || node!.seeking || !node!.paused || now < releaseUntil || Math.abs(ahead) > frameLength / 2) schedule();
      else lastTick = 0;
    }
    function resize() {
      if (Math.abs(window.innerWidth - viewportWidth) > 2) {
        const progress = Math.min(1, Math.max(0, -track!.getBoundingClientRect().top / travel));
        viewportWidth = window.innerWidth;
        travel = window.innerHeight * 7;
        track!.style.setProperty("--room-scroll-distance", `${travel}px`);
        window.scrollTo({ top: track!.getBoundingClientRect().top + window.scrollY + progress * travel, behavior: "instant" });
      }
      sync();
    }
    function wheel(event: WheelEvent) {
      if (event.ctrlKey) return;
      wakeDecoder();
      const now = performance.now();
      if (now - wheelAt > 150) motion.begin();
      const elapsed = Math.max(16, now - wheelAt);
      wheelAt = now;
      track!.dataset.roomInput = "wheel";
      window.clearTimeout(wheelRelease);
      const pixels = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1);
      wheelRelease = window.setTimeout(() => {
        motion.release(pixels / elapsed * 1000 * ROOM_OUTRO_START / travel, performance.now());
        releaseUntil = performance.now() + 650; schedule();
      }, 100);
    }
    function touchBegin(event: TouchEvent) {
      if (event.touches.length !== 1 || (event.target as HTMLElement)?.closest("a, button")) return;
      motion.begin(); releaseUntil = 0; touchSpeed = 0;
      touchY = event.touches[0].clientY; touchAt = performance.now();
      wakeDecoder();
      track!.dataset.roomInput = "touch";
      track!.dataset.roomTouches = String(Number(track!.dataset.roomTouches || 0) + 1);
    }
    function touchMove(event: TouchEvent) {
      if (event.touches.length !== 1 || touchY === null) { touchY = null; return; }
      const now = performance.now(), y = event.touches[0].clientY;
      const speed = (touchY - y) / Math.max(12, now - touchAt) * 1000 * ROOM_OUTRO_START / travel;
      touchSpeed = touchSpeed * .35 + speed * .65;
      touchY = y; touchAt = now;
    }
    function touchEnd() {
      if (touchY !== null) {
        const now = performance.now();
        motion.release(now - touchAt < 100 ? touchSpeed : 0, now);
        wakeDecoder();
        releaseUntil = now + 650; schedule();
      }
      touchY = null;
    }
    function touchCancel() { touchY = null; motion.begin(); }
    function key(event: KeyboardEvent) {
      if ((event.target as HTMLElement)?.closest("a, button, input, textarea, select, [contenteditable=true]")) return;
      if (["ArrowDown", "ArrowUp", "PageDown", "PageUp", "Home", "End", " "].includes(event.key)) {
        wakeDecoder();
        motion.begin(); track!.dataset.roomInput = "keyboard";
      }
    }
    function seeked() { publish(); schedule(); }
    function error() { setFailed(true); }
    node.addEventListener("loadedmetadata", sync); node.addEventListener("loadeddata", sync);
    node.addEventListener("seeked", seeked); node.addEventListener("error", error);
    window.addEventListener("scroll", sync, { passive: true }); window.addEventListener("resize", resize);
    window.addEventListener("wheel", wheel, { passive: true });
    window.addEventListener("touchstart", touchBegin, { passive: true });
    window.addEventListener("touchmove", touchMove, { passive: true });
    window.addEventListener("touchend", touchEnd); window.addEventListener("touchcancel", touchCancel); window.addEventListener("keydown", key);
    sync();
    return () => {
      disposed = true;
      // This same video is already running the final shot after navigation.
      if (phaseRef.current !== "outro") node.pause();
      cancelAnimationFrame(frame); window.clearTimeout(wheelRelease);
      root.classList.remove("room-scrolling");
      if (previousDistance) track.style.setProperty("--room-scroll-distance", previousDistance);
      else track.style.removeProperty("--room-scroll-distance");
      node.removeEventListener("loadedmetadata", sync); node.removeEventListener("loadeddata", sync);
      node.removeEventListener("seeked", seeked); node.removeEventListener("error", error);
      window.removeEventListener("scroll", sync); window.removeEventListener("resize", resize); window.removeEventListener("wheel", wheel);
      window.removeEventListener("touchstart", touchBegin); window.removeEventListener("touchmove", touchMove);
      window.removeEventListener("touchend", touchEnd); window.removeEventListener("touchcancel", touchCancel); window.removeEventListener("keydown", key);
    };
  }, [canScrub, failed, video]);

  const current = canScrub && !failed  ? roomCues.find(cue => time >= cue.start && time < cue.end) : undefined;
  return <main data-room-phase="scrub" data-room-time={time.toFixed(3)} ref={section} className={`room-intro ${canScrub && !failed ? "room-intro-scroll room-intro-shared" : ""}`} aria-label="���������� � ������� ����������">
    <div className="room-stage">
      {(!canScrub || failed) && <div className="room-ambient" aria-hidden="true" />}
      <header className="room-intro-header">
        <button className="room-control" onClick={finish}>{returning ? "� ����" : "����������"}<ArrowRight size={17} /></button>
      </header>
      {(!canScrub || failed) && <div className="room-film"><img className="room-still" src={`${import.meta.env.BASE_URL}media/room/start-v12.webp`} alt="����� �� ����� � �������: ������ �����, ����� ������ � ������ ������� �������" /></div>}
      {!failed && canScrub && roomCues.map(cue => <div key={cue.id} data-cue={cue.id} className={`room-cue-layer ${current?.id === cue.id ? "is-active" : ""}`} aria-hidden={current?.id !== cue.id}>
          <aside className={`room-cue room-cue-${cue.side}`} style={{ top: `max(${cue.top}%, 92px)` }}>
            <h2>{cue.title}</h2><p>{cue.text}</p>
          </aside>
        </div>)}
      {(failed || !canScrub) && <section className="room-start-card">
        <span className="room-eyebrow">����������</span>
        <h1>��������� ����.<br />������ ������ ����.</h1>
        <p>{failed ? "����� �� �����������. ����� ����� ������� ������." : "�������� ���������� ��������. �������� ����� �������� � ��������� �� ����������."}</p>
        {!failed && <button className="room-primary" onClick={() => { window.scrollTo({ top: 0, behavior: "instant" }); setAllowMotion(true); }}><ArrowDown size={18} />�������� ��������</button>}
        <button className={failed ? "room-primary" : "room-text-button"} onClick={finish}>{returning ? "������� ���" : "������� �� �����"}<ArrowRight size={17} /></button>
      </section>}
      <footer className="room-intro-footer">
        {!failed && canScrub && <p className="room-scroll-hint"><ArrowDown size={18} aria-hidden="true" />{time < .5 ? "�������� ����, ����� ����� ������" : "�������� ������ � ����� ��� �� ����"}</p>}
        <div className="room-controls-row"><Link className="room-control" to="/first-aid">������� ������ � 112</Link></div>
        <div className="room-progress" role="progressbar" aria-label="����������" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}><span style={{ transform: `scaleX(${progress})` }} /></div>
        <p className="sr-only" role="status">{current ? `${current.title}. ${current.text}` : ""}</p>
      </footer>
    </div>
  </main>;
}
