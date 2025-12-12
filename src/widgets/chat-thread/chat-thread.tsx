import { useChatStore } from '@/entities/chat/model/chat.store';
import MarkdownRenderer from '@/shared/components/MarkdownRenderer';
import { cn } from '@/shared/lib/utils';
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/ui/avatar';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Bot, Clipboard, Loader2, RefreshCw } from 'lucide-react';
import { useMemo } from 'react';

type Props = {
  onRegenerate?: () => void;
};

export function ChatThread({ onRegenerate }: Props) {
  const messages = useChatStore((state) => state.messages);

  const hasMessages = useMemo(() => messages.length > 0, [messages.length]);

  const handleCopy = (text: string) => {
    navigator.clipboard?.writeText(text).catch(() => undefined);
  };

  return (
    <div className="flex flex-col gap-3 px-2 pb-3">
      {!hasMessages && (
        <div className="rounded-[var(--radius)] border border-dashed border-border bg-card/60 p-5 text-center text-sm text-muted-foreground">
          Нет сообщений. Задайте вопрос или выберите подсказку справа.
        </div>
      )}

      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            'group flex w-full flex-col gap-3 rounded-[var(--radius)] border border-transparent p-3 transition',
            message.role === 'assistant'
              ? 'bg-primary/10 hover:border-primary/35'
              : 'bg-card hover:border-border',
          )}
        >
          <div
            className={cn('flex justify-between gap-2 border-b pb-3', {
              'border-primary/35 dark:border-primary/25':
                message.role === 'assistant',
              'border-foreground/15': message.role === 'user',
            })}
          >
            <div className="flex gap-2">
              {message.role === 'assistant' ? (
                <div className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-primary/20">
                  <Bot className="h-5 w-5 text-accent dark:text-primary" />
                </div>
              ) : (
                <Avatar>
                  <AvatarImage src="Иванов Иван" alt="@shadcn" />
                  <AvatarFallback>ИИ</AvatarFallback>
                </Avatar>
              )}
              <div className="flex flex-col gap-2 text-xs text-muted-foreground">
                <span className="font-semibold">
                  {message.role === 'assistant' ? 'Super Chat' : 'Вы'}
                </span>
                {message.serverIds && message.serverIds.length > 0 && (
                  <Badge variant="outline" className="text-[10px]">
                    {message.serverIds.join(', ')}
                  </Badge>
                )}
              </div>
            </div>
            {message.status === 'streaming' && (
              <span className="flex items-center gap-1 text-[11px] text-primary">
                <Loader2 className="h-3 w-3 animate-spin" /> В работе
              </span>
            )}
            {message.status === 'error' && (
              <span className="text-[11px] font-semibold text-destructive">
                Ошибка
              </span>
            )}
          </div>

          <div className="flex-1 space-y-2 overflow-hidden">
            <div className="max-w-none whitespace-normal px-2 text-foreground">
              {message.role === 'assistant' ? (
                <>
                  {message.content.length === 0 && (
                    <span className="flex animate-pulse items-center gap-1 text-[11px] text-primary">
                      Ожидаем ответа от агента...
                    </span>
                  )}
                  <MarkdownRenderer content={message.content} />
                </>
              ) : (
                <p className="whitespace-pre-wrap break-all">
                  {message.content}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 opacity-0 transition group-hover:opacity-100">
              {message.role === 'assistant' && message.status === 'done' && (
                <>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="rounded-[var(--radius)] text-xs"
                    onClick={() => handleCopy(message.content)}
                  >
                    <Clipboard className="mr-1 h-3.5 w-3.5" />
                    Копировать
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="rounded-[var(--radius)] text-xs"
                    onClick={onRegenerate}
                  >
                    <RefreshCw className="mr-1 h-3.5 w-3.5" />
                    Перегенерировать
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
