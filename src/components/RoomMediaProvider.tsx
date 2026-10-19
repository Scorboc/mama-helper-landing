import { useRef, type ReactNode } from "react";
import { RoomMedia } from "@/lib/room-media";

export default function RoomMediaProvider({ children }: { children: ReactNode }) {
  const video = useRef<HTMLVideoElement>(null);
  return <RoomMedia.Provider value={video}>{children}</RoomMedia.Provider>;
}
