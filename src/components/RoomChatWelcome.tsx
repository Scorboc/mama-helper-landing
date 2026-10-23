import type { ReactNode, Ref } from "react";

export function RoomChatFeed({ enabled, empty = false, scrollRef, children }: { enabled: boolean; empty?: boolean; scrollRef: Ref<HTMLDivElement>; children: ReactNode }) {
  return enabled ? <div className={`room-chat-scroll${empty ? " room-chat-scroll--empty" : ""}`} ref={scrollRef} tabIndex={0} aria-label="��������� ����">{children}</div> : <>{children}</>;
}

export function RoomChatOptions({ enabled, remaining, children }: { enabled: boolean; remaining?: number; children: ReactNode }) {
  return enabled ? <details className="room-chat-options"><summary>������� � ���������</summary>{remaining !== undefined && <p className="room-quota">�������� �������: {remaining}</p>}{children}</details> : <>{children}</>;
}
export default function RoomChatWelcome({ hasProfile, compact = false }: { hasProfile: boolean; compact?: boolean }) {
  return <div className="room-chat-welcome">
    <h2>� �����.</h2>
    <p>����� �������� ��� ���, ��� �������.</p>
    {!compact && <>
      <p className="room-welcome-topics">���, �������, ���� � ���� ������������. {!hasProfile && "��� ������� �� �������� ��������� �������."}</p>
      <p className="room-medical-note">�������������� ��������. �������� � ���������� � � �����.</p>
    </>}
  </div>;
}
