import { create } from 'zustand';
import { type ChatMessage } from '../types';

type ChatState = {
  messages: ChatMessage[];
  isStreaming: boolean;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  appendToMessage: (id: string, chunk: string) => void;
  clearMessages: () => void;
  setStreaming: (value: boolean) => void;
};

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  updateMessage: (id, patch) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, ...patch } : msg,
      ),
    })),
  appendToMessage: (id, chunk) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id ? { ...msg, content: `${msg.content}${chunk}` } : msg,
      ),
    })),
  clearMessages: () => set({ messages: [] }),
  setStreaming: (value) => set({ isStreaming: value }),
}));
