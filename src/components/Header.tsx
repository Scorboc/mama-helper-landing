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
      <div className="glass-nav mx-auto flex max-w-[1120px] items-center justify-between gap-3 rounded-[18px] px-3 py-2">
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
            className="glass-btn hidden px-5 py-2.5 text-[13px] font-semibold sm:block"
          >
            Личный кабинет
          </a>
          <button
            aria-label="Меню"
            onClick={() => setOpen((v) => !v)}
            className="glass-pill grid h-9 w-9 place-items-center lg:hidden"
          >
            <Icon name={open ? 'X' : 'Menu'} size={18} />
          </button>
        </div>
      </div>

      {open && (
        <div className="glass-nav mx-auto mt-2 max-w-[1120px] rounded-[18px] p-2 lg:hidden">
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