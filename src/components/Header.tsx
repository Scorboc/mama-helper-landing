import { useState } from 'react';
import Icon from '@/components/ui/icon';

const links = [
  { href: '#voices', label: 'Чем поможем' },
  { href: '#how', label: 'Как это работает' },
  { href: '#pricing', label: 'Мамам и папам' },
];

const Header = () => {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 px-3 pt-3 sm:px-5 sm:pt-5">
      <div className="mx-auto flex max-w-[1120px] items-center justify-between gap-3 rounded-[14px] bg-card/95 px-3 py-2 backdrop-blur">
        <a href="#top" className="flex items-center gap-2">
          <img src="/logo-mark.png" alt="Мамин помощник" className="h-10 w-auto" />
          <span className="font-heading text-[15px] font-medium">Мамин помощник</span>
        </a>

        <nav className="hidden items-center gap-1 lg:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-full px-3 py-2 text-[13px] text-muted-foreground transition-colors hover:bg-inner hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <a
            href="/cabinet"
            className="hidden rounded-full bg-gradient-to-r from-violet to-blue px-5 py-2.5 text-[13px] font-semibold text-white shadow-[0_6px_16px_-6px_hsl(258_62%_49%_/_0.6)] transition-transform hover:-translate-y-0.5 sm:block"
          >
            Личный кабинет
          </a>
          <button
            aria-label="Меню"
            onClick={() => setOpen((v) => !v)}
            className="grid h-9 w-9 place-items-center rounded-[11px] bg-inner lg:hidden"
          >
            <Icon name={open ? 'X' : 'Menu'} size={18} />
          </button>
        </div>
      </div>

      {open && (
        <div className="mx-auto mt-2 max-w-[1120px] rounded-[14px] bg-card p-2 lg:hidden">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="block rounded-[10px] px-3 py-2.5 text-sm text-muted-foreground hover:bg-inner hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
          <a
            href="/cabinet"
            onClick={() => setOpen(false)}
            className="mt-1 block rounded-[10px] bg-primary px-3 py-2.5 text-center text-sm font-medium text-primary-foreground"
          >
            Личный кабинет
          </a>
        </div>
      )}
    </header>
  );
};

export default Header;
