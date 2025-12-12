export type ChatRole = 'user' | 'assistant';

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  status?: 'idle' | 'streaming' | 'done' | 'error';
  serverIds?: string[];
};

export type ChatHistoryItem = {
  id: string;
  title: string;
  preview: string;
  updatedAt: string;
};

export type QuickPrompt = {
  id: string;
  title: string;
  prompt: string;
  tone?: string;
};

export type SendMessagePayload = {
  message: string;
  serverIds: string[];
  tool?: string;
};
