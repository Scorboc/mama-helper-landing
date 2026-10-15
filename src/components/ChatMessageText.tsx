import { Fragment } from "react";

/** Render authored emphasis as React nodes; never interpret model output as HTML. */
export default function ChatMessageText({ text }: { text: string }) {
  return <>{text.split(/(\*\*[^*\n]+\*\*)/g).map((part, index) =>
    part.startsWith("**") && part.endsWith("**")
      ? <strong key={index}>{part.slice(2, -2)}</strong>
      : <Fragment key={index}>{part}</Fragment>
  )}</>;
}
