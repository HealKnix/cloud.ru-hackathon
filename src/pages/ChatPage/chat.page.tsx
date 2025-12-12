import { useAgentStateStore } from '@/entities/agent/model/shared-state.store';
import { useChatStore } from '@/entities/chat/model/chat.store';
import { useChatController } from '@/features/chat-send/model/use-chat-controller';
import { ChatInput } from '@/features/chat-send/ui/chat-input';
import { useMcpServers } from '@/features/mcp-toggle/model/use-mcp-servers';
import { McpDrawer } from '@/features/mcp-toggle/ui/mcp-drawer';
import { useTheme } from '@/shared/lib/theme';
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/ui/avatar';
import { Button } from '@/shared/ui/button';
import {
  Drawer,
  DrawerContent,
  DrawerDescription,
  DrawerTitle,
  DrawerTrigger,
} from '@/shared/ui/drawer';
import { ChatThread } from '@/widgets/chat-thread/chat-thread';
import { ChatToolbar } from '@/widgets/chat-toolbar/chat-toolbar';
import { HistoryPanel } from '@/widgets/history-panel/history-panel';
import { Bell, ChevronDown, Moon, Settings, Sun } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

export function ChatPage() {
  const { theme, setTheme } = useTheme();
  const { sendMessage, isStreaming } = useChatController();
  const clearMessages = useChatStore((state) => state.clearMessages);
  const messages = useChatStore((state) => state.messages);
  const resetAgentState = useAgentStateStore((state) => state.resetState);
  useMcpServers();

  const chatThreadWrapper = useRef<HTMLDivElement | null>(null);

  const [draft, setDraft] = useState('');
  const [isMcpOpen, setIsMcpOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const lastUserMessage = useMemo(
    () => [...messages].reverse().find((msg) => msg.role === 'user'),
    [messages],
  );

  const handleRegenerate = () => {
    if (lastUserMessage) {
      sendMessage(lastUserMessage.content);
    }
  };

  const handleClearChat = () => {
    clearMessages();
    resetAgentState();
  };

  useEffect(() => {
    if (!chatThreadWrapper.current) return;

    chatThreadWrapper.current.scrollBy({
      top: Number.MAX_SAFE_INTEGER,
    });
  }, [messages.length, chatThreadWrapper]);

  return (
    <div className="min-h-screen overflow-hidden bg-background">
      <div className="mx-auto grid h-dvh max-w-7xl grid-rows-[0fr,1fr] sm:px-3 sm:py-4">
        <header className="flex flex-none items-center justify-between gap-3 border border-border bg-content/90 px-3 py-3 shadow-soft sm:rounded-[var(--radius)] sm:py-1">
          <img src="/cloud-logo.svg" alt="logo" width={32} className="ml-2" />
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="rounded-[var(--radius)]"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              aria-label="toggle theme"
            >
              {theme === 'light' ? (
                <Moon className="h-5 w-5" />
              ) : (
                <Sun className="h-5 w-5" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-[var(--radius)]"
            >
              <Bell className="h-5 w-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-[var(--radius)]"
              onClick={() => setIsMcpOpen(true)}
            >
              <Settings className="h-5 w-5" />
            </Button>
            <div className="flex items-center gap-2 rounded-[var(--radius)] border-border px-3 py-2">
              <Avatar>
                <AvatarImage alt="Иванов Иван" />
                <AvatarFallback>ИИ</AvatarFallback>
              </Avatar>
              <div className="leading-tight">
                <p className="text-sm font-semibold">Иванов Иван</p>
                <p className="text-xs text-muted-foreground">Product ops</p>
              </div>
              <ChevronDown className="ml-1 h-4 w-4 text-muted-foreground" />
            </div>
          </div>
        </header>

        <div className="grid gap-2 overflow-hidden lg:grid-cols-[2fr,1fr]">
          <div className="relative flex flex-col justify-end overflow-auto">
            <div className="flex-1 overflow-hidden rounded-b-[var(--radius)]">
              <div
                ref={chatThreadWrapper}
                className="h-full overflow-auto pb-[225px] pt-3"
              >
                <ChatThread onRegenerate={handleRegenerate} />
              </div>
            </div>
            <div className="absolute bottom-0 left-0 right-0">
              <ChatInput
                value={draft}
                onChangeValue={setDraft}
                onSend={(message) => {
                  sendMessage(message);
                  setDraft('');
                }}
                isSending={isStreaming}
              />
            </div>
          </div>

          <div className="hidden flex-col gap-3 overflow-auto pt-3 lg:flex">
            <ChatToolbar
              onClear={handleClearChat}
              onNewChat={() => {
                handleClearChat();
                setDraft('');
              }}
            />

            <HistoryPanel
              onPromptPick={(prompt) => {
                setDraft(prompt);
              }}
            />
          </div>
        </div>

        <div className="lg:hidden">
          <Drawer open={isHistoryOpen} onOpenChange={setIsHistoryOpen}>
            <DrawerTrigger asChild>
              <Button className="w-full rounded-[var(--radius)] bg-muted text-foreground">
                Открыть подсказки и историю
              </Button>
            </DrawerTrigger>
            <DrawerContent>
              <DrawerTitle />
              <DrawerDescription />
              <HistoryPanel
                onPromptPick={(prompt) => {
                  setDraft(prompt);
                  setIsHistoryOpen(false);
                }}
                classNames="border-none"
              />
            </DrawerContent>
          </Drawer>
        </div>

        <McpDrawer
          open={isMcpOpen}
          onOpenChange={setIsMcpOpen}
          trigger={null}
        />
      </div>
    </div>
  );
}
