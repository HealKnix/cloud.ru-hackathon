import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Sparkles } from 'lucide-react';
import { useToolAutocomplete } from '../model/use-tool-autocomplete';

type Props = {
  query: string;
  visible: boolean;
  onSelect: (command: string) => void;
};

export function ToolHints({ query, visible, onSelect }: Props) {
  const { tools } = useToolAutocomplete(query);

  if (!visible || tools.length === 0) return null;

  return (
    <div className="shadow-floating absolute bottom-[110%] left-0 right-0 z-30 overflow-hidden rounded-[var(--radius)] border border-border bg-content p-3 pr-0">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-muted-foreground">
        <Sparkles className="h-4 w-4 text-primary" />
        MCP инструменты ({tools.length})
      </div>
      <div className="grid max-h-[250px] gap-2 overflow-auto pr-3 sm:max-h-[350px]">
        {tools.map((tool) => (
          <Button
            key={tool.id}
            variant="ghost"
            onClick={() => onSelect(tool.command)}
            className="group flex min-h-fit w-full items-start justify-between gap-3 rounded-[var(--radius)] border border-transparent px-2 py-2 text-left shadow-[inset_0_0_0_0_hsl(var(--primary))] transition-shadow focus-visible:shadow-[inset_0_0_0_2px_hsl(var(--primary))] focus-visible:outline-0"
          >
            <div>
              <p className="text-sm font-semibold text-foreground group-hover:text-primary">
                /{tool.command}
              </p>
              <p className="text-xs text-muted-foreground">
                {tool.description}
              </p>
            </div>
            <Badge variant="outline" className="text-[10px]">
              {tool.serverName}
            </Badge>
          </Button>
        ))}
      </div>
    </div>
  );
}
