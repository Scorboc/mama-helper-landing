import { useEffect, useRef, type ReactNode } from "react";
import { Plus } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export type RoomChatPanel = "quick" | "options" | null;

export function RoomChatShortcut({ onOpen }: { onOpen: () => void }) {
  return <div className="room-chat-shortcuts" aria-label="Инструменты чата">
    <button type="button" onClick={onOpen} aria-haspopup="dialog"><Plus size={20} />Быстрые отметки</button>
  </div>;
}

export default function RoomChatTools({ panel, onPanelChange, quickCare, children }: {
  panel: RoomChatPanel;
  onPanelChange: (panel: RoomChatPanel) => void;
  quickCare: ReactNode;
  children: ReactNode;
}) {
  const lastPanel = useRef(panel);
  useEffect(() => { if (panel) lastPanel.current = panel; }, [panel]);
  return <Dialog open={panel !== null} onOpenChange={open => { if (!open) onPanelChange(null); }}>
      <DialogContent className="room-tools-dialog" onCloseAutoFocus={event => {
        // A newly opened profile dialog owns focus during a dialog handoff.
        if (document.querySelector('[role="dialog"][data-state="open"]')) return;
        const selector = lastPanel.current === "quick" ? ".room-chat-shortcuts button" : ".room-chat-notch";
        const target = document.querySelector<HTMLElement>(selector) || document.querySelector<HTMLElement>(".room-chat-notch");
        if (target && target.getClientRects().length) { event.preventDefault(); target.focus(); }
      }}>
        <DialogHeader>
          <DialogTitle>{panel === "quick" ? "Быстрые отметки" : "Диалоги и настройки"}</DialogTitle>
          <DialogDescription>{panel === "quick" ? "Сон, кормления и наблюдения для выбранного профиля." : "История разговоров, формат ответов и настройки аккаунта."}</DialogDescription>
        </DialogHeader>
        <div className="room-tools-content">{panel === "quick" ? quickCare : children}</div>
      </DialogContent>
    </Dialog>;
}
