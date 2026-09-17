import { useEffect, useState } from 'react';
import { Clock3, Moon, Sun } from 'lucide-react';

type Mode = 'auto' | 'light' | 'dark';
type ThemeState = { mode: Mode; theme: 'light' | 'dark' };
declare global {
  interface Window { mamaTheme: { get(): ThemeState; set(mode: Mode): ThemeState } }
}

export function useAppTheme() {
  const [state, setState] = useState<ThemeState>(() => window.mamaTheme.get());
  useEffect(() => {
    const change = (event: Event) => setState((event as CustomEvent<ThemeState>).detail);
    window.addEventListener('mama-theme-change', change);
    return () => window.removeEventListener('mama-theme-change', change);
  }, []);
  return state;
}

export default function ThemeControl() {
  const { mode } = useAppTheme();
  const Icon = mode === 'auto' ? Clock3 : mode === 'dark' ? Moon : Sun;
  return <label className="theme-control" title="Авто: тёмная тема с 20:00 до 07:00 по времени устройства">
    <Icon size={17} aria-hidden="true" />
    <select aria-label="Цветовая тема" value={mode} onChange={event => window.mamaTheme.set(event.target.value as Mode)}>
      <option value="auto">Авто</option>
      <option value="light">Светлая</option>
      <option value="dark">Тёмная</option>
    </select>
  </label>;
}
