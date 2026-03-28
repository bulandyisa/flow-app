interface StatusBadgeProps {
  status: string;
  label?: string;
}

const STATUS_CONFIG: Record<string, { icon: string; color: string; bg: string; text: string }> = {
  accepted: { icon: '●', color: 'text-green-400', bg: 'bg-green-900/40', text: 'Принято' },
  generated: { icon: '●', color: 'text-yellow-400', bg: 'bg-yellow-900/40', text: 'На ревью' },
  pending: { icon: '○', color: 'text-gray-400', bg: 'bg-gray-700/40', text: 'Ожидание' },
  rejected: { icon: '●', color: 'text-red-400', bg: 'bg-red-900/40', text: 'Отклонено' },
  skipped: { icon: '⏭', color: 'text-gray-500', bg: 'bg-gray-700/30', text: 'Пропущен' },
  generating: { icon: '◌', color: 'text-blue-400', bg: 'bg-blue-900/40', text: 'Генерация' },
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.color}`}>
      <span>{config.icon}</span>
      <span>{label || config.text}</span>
    </span>
  );
}
