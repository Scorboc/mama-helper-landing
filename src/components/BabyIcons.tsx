type IconProps = {
  className?: string;
};

const c = {
  pink: 'hsl(var(--pink))',
  pinkSoft: 'hsl(var(--pink-soft))',
  sage: 'hsl(var(--sage))',
  sageSoft: 'hsl(var(--sage-soft))',
  cream: 'hsl(var(--cream))',
  gold: 'hsl(var(--gold))',
  night: 'hsl(var(--night))',
  fur: 'hsl(var(--fur))',
  mark: 'hsl(var(--mark))',
  text: 'hsl(var(--foreground))',
  card: 'hsl(var(--card))',
};

/** Соска-пустышка */
export const Pacifier = ({ className }: IconProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <ellipse cx="30" cy="38" rx="17" ry="13" fill={c.pink} />
    <ellipse cx="30" cy="38" rx="9" ry="6.5" fill={c.cream} />
    <path d="M30 25 q-7 -8 0 -14 q7 6 0 14z" fill={c.gold} />
    <circle cx="30" cy="10" r="4.5" fill={c.mark} />
  </svg>
);

/** Слюнявчик */
export const Bib = ({ className }: IconProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <path
      d="M18 14 q12 8 24 0 q10 6 10 20 q0 18 -22 20 q-22 -2 -22 -20 q0 -14 10 -20z"
      fill={c.sageSoft}
    />
    <path d="M22 15 q8 6 16 0 q-8 8 -16 0z" fill={c.card} />
    <circle cx="30" cy="36" r="8" fill={c.card} />
    <circle cx="27" cy="34" r="1.8" fill={c.text} />
    <circle cx="33" cy="34" r="1.8" fill={c.text} />
    <path d="M27 39 q3 3 6 0" stroke={c.text} strokeWidth="1.6" fill="none" strokeLinecap="round" />
  </svg>
);

/** Погремушка */
export const Rattle = ({ className }: IconProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <circle cx="24" cy="22" r="15" fill={c.mark} />
    <circle cx="19" cy="18" r="3.2" fill={c.card} />
    <circle cx="29" cy="17" r="2.4" fill={c.card} />
    <circle cx="25" cy="27" r="2.8" fill={c.card} />
    <rect x="32" y="32" width="8" height="20" rx="4" transform="rotate(-38 36 42)" fill={c.fur} />
    <circle cx="44" cy="50" r="5" fill={c.pink} />
  </svg>
);

/** Бутылочка */
export const Bottle = ({ className }: IconProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <path d="M26 6 h8 v7 h-8z" fill={c.gold} />
    <rect x="22" y="13" width="16" height="6" rx="3" fill={c.pink} />
    <rect x="20" y="19" width="20" height="35" rx="9" fill={c.cream} />
    <path d="M20 36 h20 v12 q0 6 -10 6 q-10 0 -10 -6z" fill={c.sageSoft} />
    <path d="M25 25 h6 M25 31 h6" stroke={c.fur} strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

/** Игрушечный кубик */
export const Block = ({ className }: IconProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <rect x="8" y="24" width="26" height="26" rx="6" fill={c.pink} />
    <rect x="30" y="10" width="22" height="22" rx="6" fill={c.sage} />
    <text x="21" y="43" textAnchor="middle" fontSize="16" fill={c.card} fontFamily="sans-serif">
      А
    </text>
    <text x="41" y="27" textAnchor="middle" fontSize="14" fill={c.card} fontFamily="sans-serif">
      Б
    </text>
  </svg>
);

/** Коляска */
export const Stroller = ({ className }: IconProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <path d="M10 32 h34 v6 q0 8 -10 8 h-14 q-10 0 -10 -8z" fill={c.pink} />
    <path d="M27 32 a17 17 0 0 1 17 -17 v17z" fill={c.sageSoft} />
    <path d="M44 15 q9 3 9 16" stroke={c.fur} strokeWidth="3" fill="none" strokeLinecap="round" />
    <circle cx="20" cy="51" r="5" fill={c.night} />
    <circle cx="38" cy="51" r="5" fill={c.night} />
  </svg>
);

/** Носочки */
export const Socks = ({ className }: IconProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <path d="M12 12 h12 v18 q0 6 6 8 q6 3 6 9 q0 5 -7 5 q-8 0 -12 -8 q-5 -8 -5 -18z" fill={c.pinkSoft} />
    <path d="M12 12 h12 v6 h-12z" fill={c.pink} />
    <path d="M34 12 h12 v18 q0 6 5 8 q5 3 5 8 q0 5 -6 5 q-8 0 -11 -8 q-5 -8 -5 -17z" fill={c.sageSoft} />
    <path d="M34 12 h12 v6 h-12z" fill={c.sage} />
  </svg>
);

/** Сердечко-облачко */
export const HeartCloud = ({ className }: IconProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <ellipse cx="20" cy="36" rx="12" ry="10" fill={c.night} />
    <ellipse cx="38" cy="36" rx="14" ry="12" fill={c.night} />
    <ellipse cx="29" cy="28" rx="13" ry="11" fill={c.night} />
    <path
      d="M30 46 q-7 -6 -7 -11 q0 -5 4 -5 q2 0 3 2 q1 -2 3 -2 q4 0 4 5 q0 5 -7 11z"
      fill={c.pink}
    />
  </svg>
);
