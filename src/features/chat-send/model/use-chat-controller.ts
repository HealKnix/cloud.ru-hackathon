import { useChatStore } from '@/entities/chat/model/chat.store';
import { type SendMessagePayload } from '@/entities/chat/types';
import { useMcpStore } from '@/entities/mcp/model/mcp.store';
import { streamChat } from '@/shared/api/chat';
import { createId } from '@/shared/lib/id';
import { useMutation } from '@tanstack/react-query';
import { useCallback, useMemo } from 'react';

export function useChatController() {
  const addMessage = useChatStore((state) => state.addMessage);
  const appendToMessage = useChatStore((state) => state.appendToMessage);
  const updateMessage = useChatStore((state) => state.updateMessage);
  const setStreaming = useChatStore((state) => state.setStreaming);
  const streaming = useChatStore((state) => state.isStreaming);
  const servers = useMcpStore((state) => state.servers);
  const enabledServers = useMemo(
    () => servers.filter((s) => s.enabled),
    [servers],
  );

  const mutation = useMutation({
    mutationFn: async (payload: SendMessagePayload) => streamChat(payload),
  });

  const sendMessage = useCallback(
    async (message: string) => {
      const trimmed = message.trim();
      if (!trimmed) return;

      const serverIds = enabledServers.map((s) => s.id);
      const now = new Date().toISOString();
      const userMessageId = createId('user');
      const assistantMessageId = createId('assistant');

      addMessage({
        id: userMessageId,
        role: 'user',
        content: trimmed,
        createdAt: now,
        status: 'done',
        serverIds,
      });

      addMessage({
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        createdAt: now,
        status: 'streaming',
        serverIds,
      });

      setStreaming(true);

      try {
        const generator = await mutation.mutateAsync({
          message: trimmed,
          serverIds,
        });
        for await (const chunk of generator) {
          appendToMessage(assistantMessageId, chunk);
        }
        updateMessage(assistantMessageId, { status: 'done' });
      } catch (error) {
        updateMessage(assistantMessageId, {
          status: 'error',
          content: 'Не удалось получить ответ от агента.',
        });
        console.error(error);
      } finally {
        setStreaming(false);
      }
    },
    [
      addMessage,
      appendToMessage,
      enabledServers,
      mutation,
      setStreaming,
      updateMessage,
    ],
  );

  return useMemo(
    () => ({
      sendMessage,
      isStreaming: mutation.isPending || streaming,
      error: mutation.error,
    }),
    [mutation.error, mutation.isPending, sendMessage, streaming],
  );
}
