import {
  type ChatHistoryItem,
  type ChatStreamEvent,
  type QuickPrompt,
  type SendMessagePayload,
} from '@/entities/chat/types';
import { parseAguiStream } from '@/shared/lib/agui';
import { apiClient } from './client';
import {
  fetchMockHistory,
  fetchMockQuickPrompts,
  mockChatStream,
} from './mock/chat.mock';

const useMock = import.meta.env.VITE_API_MOCK === 'true';
const defaultAguiUrl = apiClient.defaults.baseURL
  ? `${apiClient.defaults.baseURL.replace(/\/$/, '')}/agui`
  : 'http://localhost:5001/api/agent';
const aguiUrl = import.meta.env.VITE_AGUI_URL ?? defaultAguiUrl;

type AguiRequestBody = {
  messages: Array<{ role: string; content: string }>;
  metadata?: Record<string, unknown>;
};

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
): AsyncGenerator<ChatStreamEvent, void, unknown> {
  if (useMock) {
    await new Promise((res) => setTimeout(res, 1500));
    yield* mockChatStream(payload);
    return;
  }

  const response = await openAguiStream({
    messages: [
      {
        role: 'user',
        content: payload.message,
      },
    ],
    metadata:
      payload.serverIds.length > 0 || payload.tool
        ? {
            mcpServers: payload.serverIds,
            tool: payload.tool,
          }
        : undefined,
  });

  if (!response.body) {
    throw new Error('Не удалось открыть AG-UI поток');
  }

  for await (const event of parseAguiStream(response.body)) {
    if (event.type === 'unknown') continue;
    yield event;
  }
}

async function openAguiStream(body: AguiRequestBody) {
  const response = await fetch(aguiUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (response.ok) return response;

  // Fallback to the minimal body if backend rejects metadata.
  const fallback = await fetch(aguiUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body.messages ? { messages: body.messages } : body),
  });

  if (!fallback.ok) {
    const detail = await response.text().catch(() => '');
    const fallbackDetail = await fallback.text().catch(() => '');
    throw new Error(
      detail || fallbackDetail || 'AG-UI endpoint вернул ошибку на запрос',
    );
  }

  return fallback;
}
