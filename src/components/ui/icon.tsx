import React from 'react';
import { ArrowLeft, ArrowRight, Check, CircleAlert, Clock, Mail, Menu, Phone, X, type LucideProps } from 'lucide-react';

// Import only the icons used by this app; a namespace import ships the whole library.
const icons: Record<string, React.FC<LucideProps>> = { ArrowLeft, ArrowRight, Check, CircleAlert, Clock, Mail, Menu, Phone, X };

interface IconProps extends LucideProps {
  name: string;
  fallback?: string;
}

const Icon: React.FC<IconProps> = ({ name, fallback = 'CircleAlert', ...props }) => {
  const IconComponent = icons[name];

  if (!IconComponent) {
    // Если иконка не найдена, используем fallback иконку
    const FallbackIcon = icons[fallback];

    // Если даже fallback не найден, возвращаем пустой span
    if (!FallbackIcon) {
      return <span className="text-xs text-gray-400">[icon]</span>;
    }

    return <FallbackIcon {...props} />;
  }

  return <IconComponent {...props} />;
};

export default Icon;
