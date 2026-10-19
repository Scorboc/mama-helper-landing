import { createContext, useContext, type MutableRefObject } from "react";

export const RoomMedia = createContext<MutableRefObject<HTMLVideoElement | null> | null>(null);

// The same DOM video survives navigation from the walk to the account/chat.
export function useRoomVideo() {
  const video = useContext(RoomMedia);
  if (!video) throw new Error("RoomMediaProvider is required");
  return video;
}
