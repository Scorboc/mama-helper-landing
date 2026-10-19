import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import RoomIntroduction from "@/components/RoomIntroduction";
import RoomGuestEntry from "@/components/RoomGuestEntry";
import { api, type Session } from "@/lib/parent-api";
import { accountForRoom, rememberRoom, ROOM_CHAT } from "@/lib/room-experience";

type Role = "checking" | "member" | "guest";

export default function Index() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // "Знакомство" opens the child walk on purpose; a plain visit goes to chat or the guest welcome.
  const introduction = params.get("intro") === "1";
  const [role, setRole] = useState<Role>("checking");
  useEffect(() => {
    // Warm the next routes while the session is checked.
    void import("./ParentWorkspace").catch(() => {});
    void import("./Account").catch(() => {});
  }, []);
  useEffect(() => {
    let active = true;
    const timeout = window.setTimeout(() => { if (active) setRole("guest"); }, 2500);
    api<Session>("session").then(() => {
      if (!active) return;
      if (introduction) { setRole("member"); return; }
      rememberRoom();
      navigate(ROOM_CHAT, { replace: true });
    }).catch(() => {
      if (active) setRole("guest");
    }).finally(() => window.clearTimeout(timeout));
    return () => { active = false; window.clearTimeout(timeout); };
  }, [introduction, navigate]);

  if (role === "checking") return <main className="room-entry-loading"><p role="status">Открываем Мамин помощник…</p><Link to="/first-aid">Срочная помощь · 112</Link></main>;
  if (introduction) return <RoomIntroduction returning={role === "member"} onComplete={(moving = false, startAt = 0) => {
    window.dispatchEvent(new CustomEvent("mama:room-exit", { detail: { moving, startAt } }));
    if (role === "member") {
      rememberRoom();
      navigate(ROOM_CHAT, { replace: true });
    } else {
      // A guest returns to the welcome screen, not to a login form.
      navigate("/", { replace: true });
    }
    window.scrollTo({ top: 0, behavior: "instant" });
  }} />;
  if (role === "guest") return <RoomGuestEntry loginPath={accountForRoom("login")} />;
  return <main className="room-entry-loading"><p role="status">Открываем чат…</p></main>;
}
