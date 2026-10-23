import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronDown, Compass, CreditCard, History, LogIn, LogOut, Settings, UserRound } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { contextLabel, type Profile } from "@/lib/parent-model";
import { accountForRoom } from "@/lib/room-experience";

export default function RoomChatMenu({ profile, disabled, signedIn = true, onProfile, onOptions, onSettings, onLogout }: {
  profile: Profile | null;
  disabled: boolean;
  signedIn?: boolean;
  onProfile: () => void;
  onOptions: () => void;
  onSettings: () => void;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);
  const forwardingFocus = useRef(false);
  function openDialog(action: () => void) {
    forwardingFocus.current = true;
    setOpen(false);
    action();
  }
  const name = profile?.childName || (profile?.stage === "pregnancy" ? "Ожидание малыша" : "Профиль ребёнка");
  return <><div className="room-chat-topbar">
    <Link className="room-chat-intro" to="/" aria-label="MAMA · на главную">MAMA</Link>
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button type="button" className="room-chat-notch" aria-label="Открыть меню помощника">
          Меню<ChevronDown size={14} aria-hidden="true" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="room-notch-panel" aria-label="Меню помощника" align="center" sideOffset={8} collisionPadding={12}
        onCloseAutoFocus={event => {
          // The next dialog owns focus; Escape still returns to the notch.
          if (forwardingFocus.current) { event.preventDefault(); forwardingFocus.current = false; }
        }}>
        <button type="button" className="room-notch-profile" disabled={disabled}
          aria-label={`Выбрать ребёнка: ${contextLabel(profile)}`} onClick={() => openDialog(onProfile)}>
          <UserRound size={22} aria-hidden="true" />
          <span><strong>{name}</strong><small>{contextLabel(profile).split(" · ").slice(1).join(" · ") || "Выбрать профиль"}</small></span>
          <ChevronDown size={16} aria-hidden="true" />
        </button>
        <div className="room-notch-actions">
          <button type="button" aria-label="Диалоги и настройки" onClick={() => openDialog(onOptions)} aria-haspopup="dialog"><History size={19} aria-hidden="true" />Диалоги и настройки</button>
          <button type="button" aria-label="Настройки аккаунта" onClick={() => { setOpen(false); onSettings(); }}><Settings size={19} aria-hidden="true" />Настройки аккаунта</button>
          <Link aria-label="Доступ и оплата" to="/billing" onClick={() => setOpen(false)}><CreditCard size={19} aria-hidden="true" />Доступ и оплата</Link>
          <Link aria-label="Знакомство" to="/?intro=1" onClick={() => setOpen(false)}><Compass size={19} aria-hidden="true" />Знакомство</Link>
        </div>
        <div className="room-notch-actions room-notch-session">
          {signedIn ? <button aria-label="Выйти из аккаунта" type="button" disabled={disabled} onClick={() => { setOpen(false); onLogout(); }}><LogOut size={19} aria-hidden="true" />Выйти из аккаунта</button> : <Link to={accountForRoom()} onClick={() => setOpen(false)}><LogIn size={19} aria-hidden="true" />Войти в аккаунт</Link>}
        </div>
      </PopoverContent>
    </Popover>
    <Link className="room-chat-help" to="/first-aid">Срочная помощь · 112</Link>
  </div>
    {signedIn && <button type="button" className="room-chat-context" disabled={disabled}
      aria-label={`Сменить профиль: ${contextLabel(profile)}`} onClick={onProfile}>
      <UserRound size={20} aria-hidden="true" />
      <span className="room-chat-context-copy"><small>Сейчас выбран</small><strong>{contextLabel(profile)}</strong></span>
      <span className="room-chat-context-change">Сменить</span><ChevronDown size={16} aria-hidden="true" />
    </button>}
  </>;
}
