import type { ReactNode, Ref } from "react";

export function RoomChatFeed({ enabled, scrollRef, children }: { enabled: boolean; scrollRef: Ref<HTMLDivElement>; children: ReactNode }) {
  return enabled ? <div className="room-chat-scroll" ref={scrollRef} tabIndex={0} aria-label="Сообщения чата">{children}</div> : <>{children}</>;
}

export function RoomChatOptions({ enabled, remaining, children }: { enabled: boolean; remaining?: number; children: ReactNode }) {
  return enabled ? <details className="room-chat-options"><summary>Диалоги и настройки</summary>{remaining !== undefined && <p className="room-quota">Осталось ответов: {remaining}</p>}{children}</details> : <>{children}</>;
}
export default function RoomChatWelcome({ hasProfile, compact = false }: { hasProfile: boolean; compact?: boolean }) {
  return <div className="room-chat-welcome">
    <h2>Я рядом.</h2>
    <p>Можно говорить обо всём, что волнует.</p>
    {!compact && <>
      <p className="room-welcome-topics">Сон, питание, игры и ваше самочувствие. {!hasProfile && "Для советов по возрасту заполните профиль."}</p>
      <p className="room-medical-note">Информационный помощник. Диагнозы и назначения — к врачу.</p>
    </>}
  </div>;
}
