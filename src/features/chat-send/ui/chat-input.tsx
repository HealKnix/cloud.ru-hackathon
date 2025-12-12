import { useMcpStore } from '@/entities/mcp/model/mcp.store';
import { ToolHints } from '@/features/tool-autocomplete/ui/tool-hints';
import LiquidGlass from '@/shared/components/LiquidGlass';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Spinner } from '@/shared/ui/spinner';
import { Textarea } from '@/shared/ui/textarea';
import { Paperclip, Send, Wand2 } from 'lucide-react';
import {
  useEffect,
  useEffectEvent,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react';

type Props = {
  onSend: (value: string) => void;
  isSending?: boolean;
  value?: string;
  onChangeValue?: (value: string) => void;
};

export function ChatInput({
  onSend,
  isSending,
  value: outerValue,
  onChangeValue,
}: Props) {
  const [value, setValue] = useState(outerValue ?? '');
  const [toolQuery, setToolQuery] = useState('');
  const [showToolHints, setShowToolHints] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const servers = useMcpStore((state) => state.servers);
  const enabledServers = useMemo(
    () => servers.filter((s) => s.enabled),
    [servers],
  );

  const activeServerLabel = useMemo(
    () =>
      enabledServers.length > 0
        ? enabledServers
            .map((server) => server.name)
            .slice(0, 3)
            .join(', ')
        : 'Нет активных MCP',
    [enabledServers],
  );

  const controlledSetValue = useEffectEvent((value: string) => setValue(value));

  useEffect(() => {
    if (outerValue && outerValue !== value) {
      controlledSetValue(outerValue);
    }
  }, [outerValue, value]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!value.trim()) return;
    onSend(value);
    setValue('');
    onChangeValue?.('');
    setToolQuery('');
    setShowToolHints(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSend(value);
      setValue('');
      onChangeValue?.('');
      setShowToolHints(false);
      return;
    }
  };

  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const nextValue = event.target.value;
    setValue(nextValue);
    onChangeValue?.(nextValue);

    const selection = event.target.selectionStart ?? nextValue.length;
    const slashIndex = nextValue.lastIndexOf('/', selection);

    if (nextValue.at(selection - 1) === ' ') {
      setShowToolHints(false);
    } else if (slashIndex !== -1) {
      const afterSlash = nextValue.slice(slashIndex + 1, selection);
      setToolQuery(afterSlash);
      setShowToolHints(true);
    } else {
      setShowToolHints(false);
    }
  };

  const handleSelectTool = (command: string) => {
    if (!textareaRef.current || !command) return;

    const start = textareaRef.current.selectionStart ?? value.length;
    const end = textareaRef.current.selectionEnd ?? value.length;
    const before = value.slice(0, start);
    const after = value.slice(end);
    const slashIndex = before.lastIndexOf('/');

    if (slashIndex >= 0) {
      const nextValue = `${before.slice(0, slashIndex + 1)}${command} ${after}`;
      setValue(nextValue);
      onChangeValue?.(nextValue);
      setShowToolHints(false);
      requestAnimationFrame(() => {
        textareaRef.current?.setSelectionRange(
          slashIndex + command.length + 2,
          slashIndex + command.length + 2,
        );
        textareaRef.current?.focus();
      });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <LiquidGlass
        tint="hsl(var(--content))"
        options={{
          frost: 0.85,
          saturation: 1.0,
          radius: 8,
          border: 0.07,
          alpha: 0.93,
          lightness: 50,
          blur: 10,
          displace: 1.5,
          xChannel: 'R',
          yChannel: 'B',
          blend: 'difference',
          scale: -180,
          r: 0,
          g: 2.5,
          b: 5,
        }}
        className="!overflow-visible rounded-[var(--radius)] border border-border p-3"
      >
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
            <Wand2 className="h-4 w-4 text-primary" />
            MCP: {activeServerLabel}
          </div>
          <Badge variant="outline" className="text-[11px]">
            Shift+Enter для новой строки
          </Badge>
        </div>

        <div className="relative mt-2">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Задайте задачу, используйте / для MCP инструментов"
            className="max-h-[320px] min-h-[120px] bg-transparent"
          />
          <ToolHints
            query={toolQuery}
            visible={showToolHints}
            onSelect={handleSelectTool}
          />
        </div>

        <div className="mt-3 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="rounded-2xl"
            >
              <Paperclip className="h-5 w-5" />
            </Button>
            <Badge variant="outline" className="text-xs">
              {enabledServers.length} MCP активны
            </Badge>
          </div>
          <Button
            type="submit"
            size={isSending ? 'icon' : 'default'}
            disabled={isSending || !value.trim()}
          >
            {isSending ? (
              <Spinner />
            ) : (
              <>
                Отправить
                <Send className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </LiquidGlass>
    </form>
  );
}
