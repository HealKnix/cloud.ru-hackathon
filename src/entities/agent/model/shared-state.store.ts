import { create } from 'zustand';

type AgentSharedState = Record<string, unknown>;

type AgentStateStore = {
  state: AgentSharedState;
  lastUpdated?: string;
  mergeState: (next: AgentSharedState) => void;
  replaceState: (next: AgentSharedState) => void;
  resetState: () => void;
};

export const useAgentStateStore = create<AgentStateStore>((set) => ({
  state: {},
  lastUpdated: undefined,
  mergeState: (next) =>
    set((prev) => ({
      state: { ...prev.state, ...next },
      lastUpdated: new Date().toISOString(),
    })),
  replaceState: (next) =>
    set({
      state: next,
      lastUpdated: new Date().toISOString(),
    }),
  resetState: () => set({ state: {}, lastUpdated: undefined }),
}));
