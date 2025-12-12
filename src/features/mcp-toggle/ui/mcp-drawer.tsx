import { useMcpStore } from '@/entities/mcp/model/mcp.store';
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from '@/shared/ui/drawer';
import { Switch } from '@/shared/ui/switch';
import { Loader2, ServerCog, ServerIcon } from 'lucide-react';
import { useMcpServers } from '../model/use-mcp-servers';

type Props = {
  trigger?: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export function McpDrawer({ trigger, open, onOpenChange }: Props) {
  const { servers, isLoading } = useMcpServers();
  const toggleServer = useMcpStore((state) => state.toggleServer);

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      {trigger && <DrawerTrigger asChild>{trigger}</DrawerTrigger>}
      <DrawerContent className="mx-auto max-w-2xl px-4 pb-6">
        <DrawerTitle />
        <DrawerDescription />
        <DrawerHeader className="flex items-center justify-between text-left">
          <div>
            <h2 className="text-lg font-semibold" id="mcp-drawer-title">
              MCP сервера
            </h2>
            <p className="text-sm text-muted-foreground">
              Выберите, какие источники агент может использовать.
            </p>
          </div>
          <div className="flex h-11 w-11 flex-none items-center justify-center rounded-[var(--radius)] bg-primary/15 dark:bg-primary/10">
            <ServerCog className="h-5 w-5 text-primary" />
          </div>
        </DrawerHeader>

        <div className="mt-2 grid gap-3">
          {isLoading && (
            <div className="flex items-center gap-3 rounded-[var(--radius)] border border-border bg-muted/50 px-4 py-3">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Загружаем список серверов...
              </span>
            </div>
          )}

          {!isLoading &&
            servers.map((server) => (
              <div
                key={server.id}
                className="rounded-[var(--radius)] border border-border bg-card p-4 shadow-soft transition-all [&:has(button[data-state=checked])]:border-primary [&:has(button[data-state=checked])]:bg-primary/5 [&:has(button[data-state=checked])]:dark:bg-primary/10 [&:has(button[data-state=checked])_.command-badge]:bg-primary/25 [&:has(button[data-state=checked])_.command-badge]:text-primary-foreground [&:has(button[data-state=checked])_.command-badge]:dark:text-primary"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-primary/15 text-primary dark:bg-primary/10">
                        <ServerIcon size={18} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold leading-tight">
                          {server.name}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {server.description}
                        </p>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {server.tools.map((tool) => (
                        <span
                          key={tool.id}
                          className="command-badge rounded-full bg-background px-2 py-0.5 text-xs"
                        >
                          {tool.command}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <Switch
                      checked={server.enabled}
                      onCheckedChange={(checked) =>
                        toggleServer(server.id, checked)
                      }
                    />
                    {server.latencyMs !== undefined && (
                      <span className="text-nowrap text-xs text-muted-foreground">
                        ~{server.latencyMs} мс
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
        </div>
      </DrawerContent>
    </Drawer>
  );
}
