import { Button } from '@/shared/ui/button';
import { Plus, Trash2, type LucideIcon } from 'lucide-react';

type ToolbarAction = {
  icon: LucideIcon;
  label: string;
  onClick: () => void;
  variant?: 'default' | 'ghost' | 'outline';
};

type Props = {
  onClear?: () => void;
  onNewChat?: () => void;
};

export function ChatToolbar({ onClear, onNewChat }: Props) {
  const actions: ToolbarAction[] = [
    {
      icon: Trash2,
      label: 'Очистить',
      onClick: onClear ?? (() => undefined),
      variant: 'ghost',
    },
    {
      icon: Plus,
      label: 'Новый',
      onClick:
        onNewChat ?? (() => window.scrollTo({ top: 0, behavior: 'smooth' })),
      variant: 'default',
    },
  ];

  return (
    <div className="flex items-center rounded-[var(--radius)] border border-border bg-content/90 px-3 py-3 shadow-soft">
      <div className="flex items-center gap-2">
        {actions.map((action) => (
          <Button
            key={action.label}
            variant={action.variant ?? 'ghost'}
            size="sm"
            className="rounded-[var(--radius)] px-3 text-xs"
            onClick={action.onClick}
          >
            <action.icon className="mr-1.5 h-4 w-4" />
            {action.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
