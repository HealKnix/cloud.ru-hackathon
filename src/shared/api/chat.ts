import {
  type ChatHistoryItem,
  type QuickPrompt,
  type SendMessagePayload,
} from '@/entities/chat/types';
import { decodeTextStream } from '@/shared/lib/stream';
import { apiClient } from './client';
import {
  fetchMockHistory,
  fetchMockQuickPrompts,
  mockChatStream,
} from './mock/chat.mock';

const useMock = import.meta.env.VITE_API_MOCK === 'true';

export async function fetchQuickPrompts(): Promise<QuickPrompt[]> {
  if (useMock) return fetchMockQuickPrompts();
  const { data } = await apiClient.get<QuickPrompt[]>('/chat/prompts');
  return data;
}

export async function fetchChatHistory(): Promise<ChatHistoryItem[]> {
  if (useMock) return fetchMockHistory();
  const { data } = await apiClient.get<ChatHistoryItem[]>('/chat/history');
  return data;
}

export async function* streamChat(
  payload: SendMessagePayload,
): AsyncGenerator<string, void, unknown> {
  if (useMock) {
    yield* mockChatStream(payload);
    return;
  }

  const response = await fetch(`${apiClient.defaults.baseURL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Failed to stream response');
  }

  for await (const chunk of decodeTextStream(response.body ?? undefined)) {
    yield chunk;
  }
}
