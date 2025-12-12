import { create } from 'zustand';
import { type McpServer } from '../types';

type McpState = {
  servers: McpServer[];
  setServers: (servers: McpServer[]) => void;
  toggleServer: (id: string, enabled: boolean) => void;
};

export function isSameServerList(prev: McpServer[], next: McpServer[]) {
  if (prev === next) return true;
  if (prev.length !== next.length) return false;

  return prev.every((p, idx) => {
    const n = next[idx];
    if (!n) return false;
    const sameTools =
      p.tools.length === n.tools.length &&
      p.tools.every((tool, tIdx) => tool.id === n.tools[tIdx]?.id);
    return p.id === n.id && p.enabled === n.enabled && sameTools;
  });
}

export const useMcpStore = create<McpState>((set) => ({
  servers: [],
  setServers: (servers) =>
    set((state) => {
      const merged = servers.map((server) => {
        const prev = state.servers.find((s) => s.id === server.id);
        return prev ? { ...server, enabled: prev.enabled } : server;
      });
      return { servers: merged };
    }),
  toggleServer: (id, enabled) =>
    set((state) => ({
      servers: state.servers.map((server) =>
        server.id === id ? { ...server, enabled } : server,
      ),
    })),
}));
