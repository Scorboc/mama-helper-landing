/** Share the visible viewport with body portals as well as the room shell.
 * No field values, key events or user data are read or retained. */
export function installInputViewport(win: Window = window, doc: Document = document) {
  const root = doc.documentElement;
  const viewport = win.visualViewport;
  let frame = 0;
  let revealFrame = 0;
  let baseline = win.innerHeight;
  let width = win.innerWidth;
  let editing = false;
  let revealedHeight = win.innerHeight;
  const editable = () => {
    const node = doc.activeElement;
    return node instanceof HTMLElement && node.matches(
      'textarea:not([readonly]):not([disabled]), input:not([readonly]):not([disabled]):not([type=checkbox]):not([type=radio]):not([type=button]):not([type=submit]):not([type=file]):not([type=hidden]), [contenteditable="true"]',
    ) ? node : null;
  };
  const reveal = () => {
    const node = editable();
    if (!node || (viewport && Math.abs(viewport.scale - 1) > .01)) return;
    const top = (viewport?.offsetTop ?? 0) + 12;
    const visibleHeight = viewport?.height ?? win.innerHeight;
    // Leave one touch target below the field for nearby Save/Next actions.
    const actionSpace = Math.min(72, Math.max(12, visibleHeight - node.getBoundingClientRect().height - 24));
    const bottom = (viewport?.offsetTop ?? 0) + visibleHeight - actionSpace;
    const delta = () => {
      const rect = node.getBoundingClientRect();
      return rect.bottom > bottom ? rect.bottom - bottom : rect.top < top ? rect.top - top : 0;
    };
    // A dialog needs its own scroll; scrolling only the page leaves its field clipped.
    for (let parent = node.parentElement; parent && parent !== doc.body; parent = parent.parentElement) {
      if (/(auto|scroll)/.test(win.getComputedStyle(parent).overflowY) && parent.scrollHeight > parent.clientHeight) {
        const rect = parent.getBoundingClientRect();
        const field = node.getBoundingClientRect();
        const lower = Math.min(bottom, rect.bottom - 12);
        const upper = Math.max(top, rect.top + 12);
        const move = field.bottom > lower ? field.bottom - lower : field.top < upper ? field.top - upper : 0;
        if (move) parent.scrollBy({ top: move, behavior: 'instant' });
      }
    }
    const move = delta();
    if (move) win.scrollBy({ top: move, behavior: 'instant' });
  };
  const sync = (ensureVisible: boolean, mayReveal = true) => {
    // Keep the pre-zoom layout and let the browser pan/zoom normally.
    if (viewport && Math.abs(viewport.scale - 1) > .01) {
      if (!editable()) {
        editing = false;
        root.dataset.inputKeyboard = 'closed';
        root.style.setProperty('--input-keyboard-overlap', '0px');
      }
      return;
    }
    if (Math.abs(win.innerWidth - width) > 80) {
      width = win.innerWidth;
      baseline = win.innerHeight;
      editing = false;
    }
    const focused = !!editable();
    const unzoomed = !viewport || Math.abs(viewport.scale - 1) <= .01;
    const height = unzoomed ? viewport?.height ?? win.innerHeight : win.innerHeight;
    const top = unzoomed ? viewport?.offsetTop ?? 0 : 0;
    if (!focused && !editing) baseline = win.innerHeight;
    baseline = Math.max(baseline, win.innerHeight);
    const overlap = Math.max(0, win.innerHeight - height - top);
    const reduced = unzoomed && (win.innerHeight - height > 120 || baseline - height > 120);
    const wasEditing = editing;
    editing = reduced && (focused || editing);
    root.style.setProperty('--input-viewport-height', `${height}px`);
    root.style.setProperty('--input-viewport-top', `${top}px`);
    root.style.setProperty('--input-keyboard-overlap', `${editing ? overlap : 0}px`);
    root.dataset.inputKeyboard = editing ? 'open' : 'closed';
    if (mayReveal && focused && unzoomed && (ensureVisible || (!wasEditing && editing) || (editing && Math.abs(height - revealedHeight) > 80))) {
      revealedHeight = height;
      win.cancelAnimationFrame(revealFrame);
      revealFrame = win.requestAnimationFrame(reveal);
    }
  };
  const schedule = (event: Event) => {
    win.cancelAnimationFrame(frame);
    frame = win.requestAnimationFrame(() => { frame = 0; sync(event.type === 'focusin'); });
  };
  // Panning updates portal coordinates, without fighting the user's scroll gesture.
  const pan = () => sync(false, false);
  viewport?.addEventListener('resize', schedule);
  viewport?.addEventListener('scroll', pan);
  win.addEventListener('resize', schedule);
  doc.addEventListener('focusin', schedule);
  doc.addEventListener('focusout', schedule);
  sync(false);
  return () => {
    viewport?.removeEventListener('resize', schedule);
    viewport?.removeEventListener('scroll', pan);
    win.removeEventListener('resize', schedule);
    doc.removeEventListener('focusin', schedule);
    doc.removeEventListener('focusout', schedule);
    win.cancelAnimationFrame(frame);
    win.cancelAnimationFrame(revealFrame);
    delete root.dataset.inputKeyboard;
    for (const name of ['--input-viewport-height', '--input-viewport-top', '--input-keyboard-overlap']) root.style.removeProperty(name);
  };
}
