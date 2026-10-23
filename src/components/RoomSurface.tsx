import { useEffect, useRef, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { isRoomLocation } from "@/lib/room-experience";
export default function RoomSurface({ children }: { children: ReactNode }) {
  const location = useLocation();
  const surface = useRef<HTMLDivElement>(null);
  const enabled = location.pathname !== "/" || isRoomLocation(location.search, location.pathname);
  const [readyPath, setReadyPath] = useState<string | null>(null);
  useEffect(() => {
    if (!enabled) return;
    let disposed = false;
    let preparing = false;
    let frame = 0;
    let timeout = 0;
    const fallback = window.setTimeout(() => { if (!disposed) setReadyPath(location.pathname); }, 1500);
    const image = new Image();
    image.src = `${import.meta.env.BASE_URL}media/room/rest-v12.webp`;
    const backdropReady = image.decode().catch(() => {});
    const check = () => {
      if (preparing || !surface.current?.querySelector(".parent-workspace, .account-card, .public-page, .account-page")) return;
      preparing = true;
      observer.disconnect();
      const assets = Promise.all([backdropReady, document.fonts.ready]);
      // A slow image or font must not keep the controls hidden indefinitely.
      const deadline = new Promise(resolve => { timeout = window.setTimeout(resolve, 1200); });
      void Promise.race([assets, deadline]).then(() => {
        window.clearTimeout(timeout);
        if (!disposed) frame = requestAnimationFrame(() => setReadyPath(location.pathname));
      });
    };
    const observer = new MutationObserver(check);
    if (surface.current) observer.observe(surface.current, { childList: true, subtree: true });
    check();
    return () => { disposed = true; window.clearTimeout(fallback); observer.disconnect(); cancelAnimationFrame(frame); window.clearTimeout(timeout); };
  }, [enabled, location.pathname]);
  return enabled ? <div className="room-surface" data-room-ready={readyPath === location.pathname} ref={surface}>{children}</div> : <>{children}</>;
}
