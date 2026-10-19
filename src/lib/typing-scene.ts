import { typingKeys, type TypingPulse, type TypingKey } from './typing-keyboard';

type Point = { x: number; y: number };
type PulseRef = { current: TypingPulse[] };
const ease = (n: number) => n * n * (3 - 2 * n);
const clamp = (n: number) => Math.max(0, Math.min(1, n));

/** A small local pose deformation, with the fingertip returned for exact key anchoring. */
function bendIndexFinger(source: HTMLCanvasElement, side: number, curl: number) {
  const posed = document.createElement('canvas');
  posed.width = 512; posed.height = 680;
  const context = posed.getContext('2d', { willReadFrequently: true });
  if (!context) throw new Error('Canvas unavailable');
  context.drawImage(source, side * source.width / 2, 0, source.width / 2, source.height,
    0, 0, posed.width, posed.height);
  const original = context.getImageData(0, 0, posed.width, posed.height);
  const result = context.createImageData(posed.width, posed.height);
  result.data.set(original.data);
  const scale = posed.width / (source.width / 2);
  const base = { x: (side === 0 ? 693 : 331) * scale, y: 610 * scale };
  const tip = { x: (side === 0 ? 858 : 173) * scale, y: 294 * scale };
  const length = Math.hypot(tip.x - base.x, tip.y - base.y);
  const direction = { x: (tip.x - base.x) / length, y: (tip.y - base.y) / length };
  const normal = { x: -direction.y, y: direction.x };
  const shortening = 40 * scale * curl;
  const bend = (side === 0 ? 22 : -22) * scale * curl;
  const shape = (along: number) => ease(clamp((along - 70 * scale) / (length - 70 * scale)));
  for (let y = Math.floor(170 * scale); y < 680 * scale; y++) {
    for (let x = 0; x < posed.width; x++) {
      const dx = x - base.x, dy = y - base.y;
      const along = dx * direction.x + dy * direction.y;
      const across = dx * normal.x + dy * normal.y;
      const weight = 1 - ease(clamp((Math.abs(across) - 65 * scale) / (50 * scale)));
      if (!weight || along <= 70 * scale) continue;
      // Inverse mapping avoids gaps where the shortened distal finger used to be.
      let sourceAlong = along;
      for (let step = 0; step < 5; step++) sourceAlong = along + shortening * shape(sourceAlong) * weight;
      const sourceAcross = across - bend * shape(sourceAlong) * weight;
      const sx = base.x + direction.x * sourceAlong + normal.x * sourceAcross;
      const sy = base.y + direction.y * sourceAlong + normal.y * sourceAcross;
      const px = Math.floor(sx), py = Math.floor(sy), fx = sx - px, fy = sy - py;
      const target = (y * posed.width + x) * 4;
      if (px < 0 || py < 0 || px + 1 >= posed.width || py + 1 >= posed.height) {
        result.data.fill(0, target, target + 4); continue;
      }
      for (let channel = 0; channel < 4; channel++) {
        const top = (py * posed.width + px) * 4 + channel;
        const bottom = top + posed.width * 4;
        result.data[target + channel] = (original.data[top] * (1 - fx) + original.data[top + 4] * fx) * (1 - fy)
          + (original.data[bottom] * (1 - fx) + original.data[bottom + 4] * fx) * fy;
      }
    }
  }
  context.putImageData(result, 0, 0);
  return { image: posed, tip: {
    x: tip.x - direction.x * shortening + normal.x * bend,
    y: tip.y - direction.y * shortening + normal.y * bend,
  } };
}

/** Approved photographic hands, composited locally. No field values enter this renderer. */
export async function mountTypingScene(host: HTMLElement, pulse: PulseRef, isActive: () => boolean) {
  const image = new Image();
  image.src = `${import.meta.env.BASE_URL}media/login-hands/child-hands.png`;
  await image.decode();
  // Suppress the generated low-alpha fringe at display time; preserve the original file.
  const matte = document.createElement('canvas');
  matte.width = image.naturalWidth; matte.height = image.naturalHeight;
  const matteContext = matte.getContext('2d', { willReadFrequently: true });
  if (!matteContext) throw new Error('Canvas unavailable');
  matteContext.drawImage(image, 0, 0);
  const pixels = matteContext.getImageData(0, 0, matte.width, matte.height);
  for (let i = 3; i < pixels.data.length; i += 4) {
    pixels.data[i] = Math.round(255 * ease(Math.max(0, Math.min(1, (pixels.data[i] - 175) / 70))));
  }
  matteContext.putImageData(pixels, 0, 0);
  const handPoses = [0, 1].map(side => ({
    resting: bendIndexFinger(matte, side, 1),
    pressing: bendIndexFinger(matte, side, 1.12),
  }));
  matte.width = matte.height = 0;
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas unavailable');
  host.appendChild(canvas);
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let width = 1, height = 1, frame = 0, last = 0, started = -Infinity;
  let selected: TypingKey | undefined;
  let side = 0;
  let dirty = true;
  const positions: Point[] = [{ x: 0, y: 0 }, { x: 0, y: 0 }];
  const homes = [typingKeys.find(k => k.code === 'KeyF')!, typingKeys.find(k => k.code === 'KeyJ')!];
  function keyRect(key: TypingKey) {
    const row = Math.round(key.z / .021 + 2);
    const unit = width * .88 / 15;
    const rowHeight = unit * .92;
    return { x: width / 2 + key.x / .021 * unit, y: height * .045 + rowHeight / 2 + row * rowHeight,
      w: key.width / .021 * unit, h: rowHeight * .88 };
  }
  function resize() {
    width = host.clientWidth; height = host.clientHeight;
    if (!width || !height) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
    ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
    homes.forEach((key, i) => { const r = keyRect(key); positions[i] = { x: r.x, y: r.y }; });
    dirty = true;
  }
  const observer = new ResizeObserver(resize); observer.observe(host); resize();
  function draw(time: number) {
    frame = requestAnimationFrame(draw);
    if (!isActive() || document.hidden) {
      pulse.current = []; selected = undefined;
    }
    const current = time - started >= 85 ? pulse.current.shift() : undefined;
    if (current) {
      selected = typingKeys.find(k => k.code === current.code);
      started = time; side = selected && selected.x > 0 ? 1 : 0; dirty = true;
    }
    const age = time - started;
    if (!dirty && age > 700) return;
    const dt = Math.min(40, time - last || 16); last = time;
    ctx!.clearRect(0, 0, width, height);
    const contact = !!selected && age >= 12 && age < 200;
    host.dataset.key = contact ? selected!.code : '';
    const keyboardHeight = width * .88 / 15 * .92 * 5 + height * .035;
    ctx!.shadowColor = '#171f162b'; ctx!.shadowBlur = 8; ctx!.shadowOffsetY = 2;
    ctx!.fillStyle = '#8b9f83'; ctx!.beginPath(); ctx!.roundRect(width * .035, height * .025, width * .93, keyboardHeight, 20); ctx!.fill();
    ctx!.strokeStyle = '#a8b79f'; ctx!.lineWidth = 2; ctx!.stroke();
    ctx!.shadowBlur = 0; ctx!.shadowOffsetY = 0;
    for (const key of typingKeys) {
      const r = keyRect(key), down = contact && selected === key;
      const y = r.y + (down ? 2 : 0);
      const color = key.width > .021 ? '#c0d1af' : '#f4eedb';
      ctx!.fillStyle = down ? '#91a67e' : '#aeb99d';
      ctx!.beginPath(); ctx!.roundRect(r.x - r.w / 2, y - r.h / 2 + 3, r.w, r.h, Math.min(6, r.h * .3)); ctx!.fill();
      ctx!.fillStyle = down ? '#aecb91' : color;
      ctx!.beginPath(); ctx!.roundRect(r.x - r.w / 2, y - r.h / 2, r.w, r.h, Math.min(6, r.h * .3)); ctx!.fill();
      ctx!.fillStyle = '#384633'; ctx!.textAlign = 'center'; ctx!.textBaseline = 'middle';
      ctx!.font = `500 ${Math.max(6, Math.min(width * (key.en.length > 2 ? .015 : .022), r.h * .52))}px Onest, sans-serif`;
      ctx!.fillText(key.en, r.x, y - (key.en !== key.ru ? r.h * .18 : 0));
      if (key.en !== key.ru) {
        ctx!.font = `${Math.max(5, Math.min(width * .014, r.h * .32))}px Onest, sans-serif`;
        ctx!.fillStyle = '#66765c'; ctx!.fillText(key.ru, r.x + r.w * .22, y + r.h * .29);
      }
    }
    positions.forEach((position, i) => {
      const moving = i === side && selected && age < 260 && !reduced.matches;
      const target = keyRect(moving ? selected! : homes[i]);
      const amount = 1 - Math.exp(-dt / 32);
      position.x += (target.x - position.x) * amount; position.y += (target.y - position.y) * amount;
      // Visible fingertip reaches the actual key centre during contact.
      if (moving && contact) { position.x = target.x; position.y = target.y; }
      const pressing = moving && contact ? 1 : 0;
      const pose = pressing ? handPoses[i].pressing : handPoses[i].resting;
      const handWidth = Math.min(width * .30, height * .69) * (pressing ? .985 : 1);
      const handHeight = handWidth * pose.image.height / pose.image.width;
      ctx!.save();
      // Align the backs of both hands and their index fingers along the overhead key grid.
      ctx!.translate(position.x, position.y + (pressing ? 2 : 0));
      ctx!.rotate(i === 0 ? -.43 : .43);
      ctx!.shadowColor = '#18201633'; ctx!.shadowBlur = pressing ? 3 : 9; ctx!.shadowOffsetY = pressing ? 1 : 6;
      ctx!.drawImage(pose.image, -handWidth * pose.tip.x / pose.image.width,
        -handHeight * pose.tip.y / pose.image.height, handWidth, handHeight);
      ctx!.restore();
    });
    dirty = false;
  }
  const mediaChange = () => { dirty = true; };
  reduced.addEventListener('change', mediaChange);
  frame = requestAnimationFrame(draw);
  return () => {
    cancelAnimationFrame(frame); observer.disconnect(); reduced.removeEventListener('change', mediaChange);
    pulse.current = []; delete host.dataset.key; canvas.remove();
    handPoses.forEach(poses => { for (const pose of [poses.resting, poses.pressing]) pose.image.width = pose.image.height = 0; });
  };
}
