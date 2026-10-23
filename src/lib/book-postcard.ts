import type { Moment } from './first-year-book';
import { formatBookDay } from './first-year-book';

// Break at words; only an oversized word is split into Unicode characters.
export function wrapBookText(text: string, width: number, measure: (s: string) => number): string[] {
    const lines: string[] = [];
    for (const paragraph of text.split('\n')) {
        let line = '';
        for (const word of paragraph.trim().split(/\s+/).filter(Boolean)) {
            if (line && measure(line + ' ' + word) <= width) { line += ' ' + word; continue; }
            if (line) { lines.push(line); line = ''; }
            for (const char of word) {
                if (line && measure(line + char) > width) { lines.push(line); line = ''; }
                line += char;
            }
        }
        lines.push(line);
    }
    return lines;
}

// No transport or persistent storage: the photo is decoded locally and closed.
export async function renderPostcard({ title, name, moments, caption, dates, brand, photo }: {
    title: string; name: string; moments: Moment[]; caption: string;
    dates: boolean; brand: boolean; photo?: File;
}) {
    const overflow = () => new Error('Для одной открытки много текста. Выберите меньше моментов или сократите подпись.');
    if (moments.length > 5) throw overflow();
    await document.fonts.ready;
    const family = getComputedStyle(document.documentElement).fontFamily || 'Onest, sans-serif';
    const canvas = document.createElement('canvas');
    canvas.width = 1080; canvas.height = 1350;
    const ctx = canvas.getContext('2d');
    if (!ctx || typeof ctx.roundRect !== 'function') throw new Error('Создание картинки недоступно в этом браузере. Обновите браузер или сохраните книгу через печать / PDF.');
    const font = (size: number, style = '') => { ctx.font = `${style} ${size}px ${family}, sans-serif`.trim(); };
    const wrap = (text: string, width = 860) => wrapBookText(text, width, s => ctx.measureText(s).width);
    font(68, '600');
    const heading = wrap(name ? `${name} · ${title.replace(/ жизни$/, '')}` : title, 920);
    font(38);
    const entries = moments.map(m => ({ lines: wrap([m.text, m.note].filter(Boolean).join(' — ')), day: dates ? formatBookDay(m.day, true) : '' }));
    font(36, 'italic');
    const signature = caption.trim() ? wrap(`«${caption.trim()}»`, 920) : [];
    const photoTop = 70 + heading.length * 80 + 24;
    const textTop = photo ? photoTop + 720 + 32 : Math.max(390, photoTop + 180);
    const end = textTop + entries.reduce((h, e) => h + e.lines.length * 48 + (e.day ? 32 : 0) + 18, 0) + signature.length * 46;
    if (end > 1240) throw overflow();
    ctx.fillStyle = '#fff8ed'; ctx.fillRect(0, 0, 1080, 1350);
    ctx.strokeStyle = '#d8c6a5'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.roundRect(32, 32, 1016, 1286, 28); ctx.stroke();
    ctx.textBaseline = 'top'; ctx.fillStyle = '#29382b'; font(68, '600');
    heading.forEach((line, i) => ctx.fillText(line, 80, 70 + i * 80));
    if (photo) {
        if (typeof createImageBitmap !== 'function') throw new Error('Этот браузер не может прочитать фото. Можно собрать открытку без фото.');
        if (!['image/jpeg', 'image/png', 'image/webp', 'image/avif', 'image/heic', 'image/heif'].includes(photo.type) || photo.size > 20 * 1024 * 1024)
            throw new Error('Выберите фото JPEG, PNG, WebP, AVIF или HEIC/HEIF размером до 20 МБ.');
        const bitmap = await createImageBitmap(photo, { imageOrientation: 'from-image', resizeWidth: 1600, resizeQuality: 'high' }).catch(() => { throw new Error('Не удалось прочитать фото. Попробуйте JPEG или PNG.'); });
        try {
            ctx.save(); ctx.shadowColor = '#29382b26'; ctx.shadowBlur = 24; ctx.shadowOffsetY = 10;
            ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.roundRect(72, photoTop - 8, 936, 736, 32); ctx.fill(); ctx.restore();
            ctx.save(); ctx.beginPath(); ctx.roundRect(80, photoTop, 920, 720, 24); ctx.clip();
            const scale = Math.max(920 / bitmap.width, 720 / bitmap.height);
            ctx.drawImage(bitmap, 80 + (920 - bitmap.width * scale) / 2, photoTop + (720 - bitmap.height * scale) / 2, bitmap.width * scale, bitmap.height * scale);
            ctx.restore();
        } finally { bitmap.close(); }
    } else {
        for (const [x, y, r, color] of [[430, 280, 72, '#eed3a2'], [560, 295, 94, '#dce2d2'], [670, 265, 45, '#e7bcaa']] as const) {
            ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, Math.max(photoTop + 80, y), r, 0, Math.PI * 2); ctx.fill();
        }
    }
    let y = textTop;
    for (const entry of entries) {
        ctx.fillStyle = '#29382b'; font(38);
        ctx.beginPath(); ctx.arc(91, y + 20, 5, 0, Math.PI * 2); ctx.fill();
        entry.lines.forEach(line => { ctx.fillText(line, 120, y); y += 48; });
        if (entry.day) { font(26); ctx.fillStyle = '#736f61'; ctx.fillText(entry.day, 120, y); y += 32; }
        y += 18;
    }
    font(36, 'italic'); ctx.fillStyle = '#725548';
    signature.forEach(line => { ctx.fillText(line, 80, y); y += 46; });
    if (brand) { font(24); ctx.fillStyle = '#736f61'; ctx.textAlign = 'center'; ctx.fillText('Мамин помощник', 540, 1270); }
    return new Promise<Blob>((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Не удалось собрать картинку.')), 'image/png'));
}
