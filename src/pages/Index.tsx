import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import RoomIntroduction from "@/components/RoomIntroduction";
import RoomGuestEntry from "@/components/RoomGuestEntry";
import { api, type Session } from "@/lib/parent-api";
import { accountForRoom, rememberRoom, ROOM_CHAT } from "@/lib/room-experience";

type Role = "checking" | "member" | "guest";

export default function Index() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // "����������" opens the child walk on purpose; a plain visit goes to chat or the guest welcome.
  const introduction = params.get("intro") === "1";
  const [role, setRole] = useState<Role>("checking");
  const sessionResult = useRef<Promise<Role> | null>(null);
  const activeSession = useRef(false);
  useEffect(() => {
    // Warm the next routes while the session is checked.
    void import("./ParentWorkspace").catch(() => {});
    void import("./Account").catch(() => {});
  }, []);
  useEffect(() => {
    let active = true;
    activeSession.current = true;
    const timeout = window.setTimeout(() => { if (active) setRole("guest"); }, 2500);
    const result = api<Session>("session").then(() => "member" as const, () => "guest" as const);
    sessionResult.current = result;
    result.then(nextRole => {
      if (nextRole === "guest") { if (active) setRole("guest"); return; }
      if (!active) return;
      if (introduction) { setRole("member"); return; }
      rememberRoom();
      navigate(ROOM_CHAT, { replace: true });
    }).catch(() => {
      if (active) setRole("guest");
    }).finally(() => window.clearTimeout(timeout));
    return () => { active = false; activeSession.current = false; window.clearTimeout(timeout); };
  }, [introduction, navigate]);

  // The public tour does not need an account: keep the first swipe while the
  // session request is pending, instead of replacing the scroll track later.
  if (role === "checking" && !introduction) return <main className="room-entry-loading"><p role="status">��������� ����� ��������</p><Link to="/first-aid">������� ������ � 112</Link></main>;
  if (introduction) return <RoomIntroduction returning={role === "member"} onComplete={async (moving = false, startAt = 0) => {
    const request = sessionResult.current;
    let waitTimer = 0;
    const fallback = new Promise<Role>(resolve => { waitTimer = window.setTimeout(() => resolve("guest"), 2500); });
    const finalRole = await Promise.race([request ?? Promise.resolve(role), fallback]);
    window.clearTimeout(waitTimer);
    if (!activeSession.current || sessionResult.current !== request) return;
    window.dispatchEvent(new CustomEvent("mama:room-exit", { detail: { moving, startAt } }));
    if (finalRole === "member") {
      rememberRoom();
      navigate(ROOM_CHAT, { replace: true });
    } else {
      // A guest returns to the welcome screen, not to a login form.
      navigate("/", { replace: true });
    }
    window.scrollTo({ top: 0, behavior: "instant" });
  }} />;
  if (role === "guest") return <RoomGuestEntry loginPath={accountForRoom("login")} />;
  return <main className="room-entry-loading"><p role="status">��������� ���</p></main>;
}
