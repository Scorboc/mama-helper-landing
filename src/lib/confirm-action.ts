/** Native modal semantics provide a focus trap and Escape cancellation. */
export function confirmAction(message: string): Promise<boolean> {
  return new Promise(resolve => {
    const previous = document.activeElement;
    const dialog = document.createElement("dialog");
    dialog.className = "confirmation-dialog";
    dialog.setAttribute("role", "alertdialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-labelledby", "confirmation-message");
    const text = document.createElement("p");
    text.id = "confirmation-message";
    text.textContent = message;
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = "Отмена";
    const accept = document.createElement("button");
    accept.type = "button";
    accept.textContent = "Продолжить";
    let finished = false;
    const finish = (accepted: boolean) => {
      if (finished) return;
      finished = true;
      dialog.close();
      dialog.remove();
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
      resolve(accepted);
    };
    cancel.onclick = () => finish(false);
    accept.onclick = () => finish(true);
    dialog.addEventListener("cancel", event => { event.preventDefault(); finish(false); });
    dialog.addEventListener("close", () => finish(false));
    dialog.append(text, cancel, accept);
    document.body.append(dialog);
    dialog.showModal();
    cancel.focus();
  });
}