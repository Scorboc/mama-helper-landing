import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import RoomSurface from "@/components/RoomSurface";
import RoomChatMenu from "@/components/RoomChatMenu";
import RoomNavigation from "@/components/RoomNavigation";
import { api, type Session } from "@/lib/parent-api";
import { clearChatDrafts } from "@/lib/chat-drafts";
import { accountForRoom } from "@/lib/room-experience";

/** Public help remains available even while the optional session is unavailable. */
export default function RoomPageShell() {
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    let active = true;
    void api<Session>("session").then(value => { if (active) setSession(value); }).catch(() => { if (active) setSession(null); });
    return () => { active = false; };
  }, [location.pathname, location.search]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
    setError("");
  }, [location.pathname]);
  async function logout() {
    setBusy(true); setError("");
    try {
      await api("logout");
      if (session) clearChatDrafts(session.user.id);
      setSession(null);
      navigate(accountForRoom());
    } catch (e) { setError(e instanceof Error ? e.message : "Не удалось выйти. Попробуйте ещё раз."); }
    finally { setBusy(false); }
  }
  return <RoomSurface><div className="room-route-shell">
    <a className="skip-link" href="#main-content">К основному содержимому</a>
    <RoomChatMenu profile={session?.state.profile ?? null} signedIn={!!session} disabled={busy}
      onProfile={() => navigate("/chat?scene=room&panel=children")}
      onOptions={() => navigate("/chat?scene=room&panel=options")}
      onSettings={() => navigate("/chat?scene=room&tab=settings")}
      onLogout={() => void logout()} />
    {error && <p role="alert" className="form-error room-route-error">{error}</p>}
    <div id="main-content" tabIndex={-1} className="room-route-content"><Outlet /></div>
    <RoomNavigation active="more" />
  </div></RoomSurface>;
}
