type CritterProps = {
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
  inner: 'hsl(var(--inner))',
};

/** Лисёнок — главный герой сервиса */
export const Fox = ({ className }: CritterProps) => (
  <svg viewBox="0 0 120 120" className={className}>
    <path d="M22 46 L28 14 L52 34 Z" fill={c.pink} />
    <path d="M98 46 L92 14 L68 34 Z" fill={c.pink} />
    <circle cx="60" cy="64" r="38" fill={c.pink} />
    <ellipse cx="60" cy="78" rx="20" ry="15" fill={c.cream} />
    <circle cx="46" cy="60" r="5" fill={c.text} />
    <circle cx="74" cy="60" r="5" fill={c.text} />
    <ellipse cx="60" cy="72" rx="5" ry="3.6" fill={c.text} />
    <circle cx="36" cy="72" r="6" fill={c.pinkSoft} />
    <circle cx="84" cy="72" r="6" fill={c.pinkSoft} />
  </svg>
);

/** Зайчонок */
export const Bunny = ({ className }: CritterProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <ellipse cx="22" cy="16" rx="5" ry="12" fill={c.cream} />
    <ellipse cx="38" cy="16" rx="5" ry="12" fill={c.cream} />
    <ellipse cx="22" cy="17" rx="2" ry="7" fill={c.pinkSoft} />
    <ellipse cx="38" cy="17" rx="2" ry="7" fill={c.pinkSoft} />
    <circle cx="30" cy="36" r="17" fill={c.cream} />
    <circle cx="24" cy="34" r="2.6" fill={c.text} />
    <circle cx="36" cy="34" r="2.6" fill={c.text} />
    <ellipse cx="30" cy="41" rx="3" ry="2.2" fill={c.pink} />
  </svg>
);

/** Совушка */
export const Owl = ({ className }: CritterProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <circle cx="30" cy="31" r="19" fill={c.sage} />
    <circle cx="23" cy="28" r="6.5" fill={c.cream} />
    <circle cx="37" cy="28" r="6.5" fill={c.cream} />
    <circle cx="23" cy="28" r="2.8" fill={c.text} />
    <circle cx="37" cy="28" r="2.8" fill={c.text} />
    <path d="M30 35 l4 5h-8z" fill={c.gold} />
  </svg>
);

/** Медвежонок */
export const Bear = ({ className }: CritterProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <circle cx="17" cy="19" r="7" fill={c.fur} />
    <circle cx="43" cy="19" r="7" fill={c.fur} />
    <circle cx="30" cy="34" r="18" fill={c.fur} />
    <circle cx="24" cy="32" r="2.6" fill={c.text} />
    <circle cx="36" cy="32" r="2.6" fill={c.text} />
    <ellipse cx="30" cy="40" rx="7" ry="5" fill={c.cream} />
    <ellipse cx="30" cy="38" rx="2.4" ry="1.8" fill={c.text} />
  </svg>
);

/** Котик */
export const Cat = ({ className }: CritterProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <path d="M14 24 L18 8 L29 18 Z" fill={c.night} />
    <path d="M46 24 L42 8 L31 18 Z" fill={c.night} />
    <circle cx="30" cy="33" r="19" fill={c.night} />
    <circle cx="23" cy="31" r="2.6" fill={c.text} />
    <circle cx="37" cy="31" r="2.6" fill={c.text} />
    <path d="M30 37 l3 3h-6z" fill={c.pink} />
    <path d="M8 34h10M8 39h10M42 34h10M42 39h10" stroke={c.cream} strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);

/** Слонёнок */
export const Elephant = ({ className }: CritterProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <circle cx="30" cy="30" r="18" fill={c.night} />
    <ellipse cx="13" cy="30" rx="7" ry="10" fill={c.night} />
    <ellipse cx="47" cy="30" rx="7" ry="10" fill={c.night} />
    <circle cx="24" cy="28" r="2.6" fill={c.text} />
    <circle cx="36" cy="28" r="2.6" fill={c.text} />
    <path d="M30 36 q0 10 6 12" stroke={c.cream} strokeWidth="5" fill="none" strokeLinecap="round" />
  </svg>
);

/** Ёжик */
export const Hedgehog = ({ className }: CritterProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <path d="M8 40 q6 -24 26 -22 q18 2 18 22z" fill={c.fur} />
    <circle cx="42" cy="32" r="11" fill={c.cream} />
    <circle cx="45" cy="30" r="2.4" fill={c.text} />
    <circle cx="51" cy="34" r="2.4" fill={c.text} />
    <path d="M14 40 h38" stroke={c.fur} strokeWidth="4" strokeLinecap="round" />
  </svg>
);

/** Овечка */
export const Sheep = ({ className }: CritterProps) => (
  <svg viewBox="0 0 60 60" className={className}>
    <circle cx="20" cy="28" r="9" fill={c.cream} />
    <circle cx="32" cy="22" r="9" fill={c.cream} />
    <circle cx="41" cy="30" r="9" fill={c.cream} />
    <circle cx="27" cy="36" r="10" fill={c.cream} />
    <circle cx="38" cy="38" r="10" fill={c.sageSoft} />
    <circle cx="35" cy="36" r="2.3" fill={c.text} />
    <circle cx="43" cy="38" r="2.3" fill={c.text} />
  </svg>
);

/** Маленький аватар в кружке */
export const AvatarCritter = ({
  variant,
  className,
}: {
  variant: 0 | 1 | 2 | 3 | 4;
  className?: string;
}) => {
  const bg = [c.pinkSoft, c.sageSoft, c.cream, c.pinkSoft, c.night][variant];
  const body = [
    <g key="fox">
      <circle cx="20" cy="22" r="12" fill={c.pink} />
      <path d="M9 12 l4-7 5 6z" fill={c.pink} />
      <path d="M31 12 l-4-7 -5 6z" fill={c.pink} />
      <circle cx="16" cy="20" r="2" fill={c.text} />
      <circle cx="24" cy="20" r="2" fill={c.text} />
    </g>,
    <g key="bunny">
      <ellipse cx="14" cy="8" rx="3.5" ry="9" fill={c.cream} />
      <ellipse cx="26" cy="8" rx="3.5" ry="9" fill={c.cream} />
      <circle cx="20" cy="24" r="12" fill={c.cream} />
      <circle cx="16" cy="22" r="2" fill={c.text} />
      <circle cx="24" cy="22" r="2" fill={c.text} />
    </g>,
    <g key="owl">
      <circle cx="20" cy="21" r="13" fill={c.sage} />
      <circle cx="15" cy="19" r="4.5" fill={c.cream} />
      <circle cx="25" cy="19" r="4.5" fill={c.cream} />
      <circle cx="15" cy="19" r="2" fill={c.text} />
      <circle cx="25" cy="19" r="2" fill={c.text} />
      <path d="M20 24 l3 4h-6z" fill={c.gold} />
    </g>,
    <g key="bear">
      <circle cx="10" cy="12" r="5" fill={c.fur} />
      <circle cx="30" cy="12" r="5" fill={c.fur} />
      <circle cx="20" cy="23" r="13" fill={c.fur} />
      <circle cx="15" cy="21" r="2" fill={c.text} />
      <circle cx="25" cy="21" r="2" fill={c.text} />
    </g>,
    <g key="cat">
      <circle cx="20" cy="22" r="12" fill={c.cream} />
      <path d="M9 13 l3-8 6 6z" fill={c.cream} />
      <path d="M31 13 l-3-8 -6 6z" fill={c.cream} />
      <circle cx="16" cy="21" r="2" fill={c.text} />
      <circle cx="24" cy="21" r="2" fill={c.text} />
    </g>,
  ][variant];

  return (
    <svg viewBox="0 0 40 40" className={className}>
      <rect width="40" height="40" fill={bg} />
      {body}
    </svg>
  );
};

export const SleepingBear = ({ className }: CritterProps) => (
  <svg viewBox="0 0 160 90" className={className}>
    <ellipse cx="80" cy="74" rx="52" ry="16" fill={c.fur} />
    <circle cx="122" cy="60" r="17" fill={c.fur} />
    <path d="M108 48 l2-12 10 8z" fill={c.fur} />
    <path d="M134 48 l-2-12 -10 8z" fill={c.fur} />
    <path d="M118 60 q4 3 8 0" stroke={c.text} strokeWidth="2" fill="none" strokeLinecap="round" />
    <path d="M28 74 q-14 -6 -18 -20 q18 10 26 6z" fill={c.cream} />
  </svg>
);

export const critterColors = c;
