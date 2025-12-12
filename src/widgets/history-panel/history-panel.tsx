import { fetchChatHistory, fetchQuickPrompts } from '@/shared/api/chat';
import { cn } from '@/shared/lib/utils';
import { Badge } from '@/shared/ui/badge';
import { Card, CardContent, CardHeader } from '@/shared/ui/card';
import { useQuery } from '@tanstack/react-query';
import { Bookmark, Clock3, MessageSquare } from 'lucide-react';

type Props = {
  onPromptPick: (prompt: string) => void;
  classNames?: string;
};

export function HistoryPanel({ onPromptPick, classNames }: Props) {
  const { data: prompts } = useQuery({
    queryKey: ['chat', 'prompts'],
    queryFn: fetchQuickPrompts,
  });
  const { data: history } = useQuery({
    queryKey: ['chat', 'history'],
    queryFn: fetchChatHistory,
  });

  return (
    <Card className={cn('bg-content shadow-none', classNames)}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <p className="text-lg font-semibold">История</p>
          <p className="text-sm text-muted-foreground">
            Последние диалоги и быстрые промпты.
          </p>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius)] bg-primary/15">
          <MessageSquare className="h-4 w-4 text-primary" />
        </div>
      </CardHeader>
      <CardContent className="space-y-4 !pt-2">
        <section>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Bookmark className="h-4 w-4 text-primary" />
            Быстрые промпты
          </div>
          <div className="grid gap-2">
            {prompts?.map((prompt) => (
              <button
                key={prompt.id}
                type="button"
                onClick={() => onPromptPick(prompt.prompt)}
                className="flex w-full items-start justify-between gap-2 rounded-[var(--radius)] border border-border px-3 py-2 text-left hover:border-primary/40 hover:bg-primary/5"
              >
                <div>
                  <p className="text-sm font-semibold">{prompt.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {prompt.prompt}
                  </p>
                </div>
                {prompt.tone && <Badge variant="outline">{prompt.tone}</Badge>}
              </button>
            ))}
          </div>
        </section>

        <section>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Clock3 className="h-4 w-4 text-primary" />
            Последние диалоги
          </div>
          <div className="grid gap-2">
            {history && history.length > 0 ? (
              history.map((item) => (
                <div
                  key={item.id}
                  className="rounded-[var(--radius)] border border-border bg-muted/40 px-3 py-2 text-sm"
                >
                  <p className="font-semibold">{item.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.preview}
                  </p>
                </div>
              ))
            ) : (
              <div className="rounded-[var(--radius)] border border-dashed border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
                История появится, когда появятся реальные диалоги.
              </div>
            )}
          </div>
        </section>
      </CardContent>
    </Card>
  );
}
