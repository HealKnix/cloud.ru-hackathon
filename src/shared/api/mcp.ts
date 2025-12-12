import { type McpServer } from '@/entities/mcp/types';
import { apiClient } from './client';
import { fetchMockServers } from './mock/mcp.mock';

const useMock = import.meta.env.VITE_API_MOCK === 'true';

export async function fetchServers(): Promise<McpServer[]> {
  if (useMock) return fetchMockServers();
  const { data } = await apiClient.get<McpServer[]>('/mcp/servers');
  return data;
}

export async function persistServerState(payload: {
  id: string;
  enabled: boolean;
}) {
  if (useMock) return payload;
  await apiClient.post(`/mcp/servers/${payload.id}/state`, {
    enabled: payload.enabled,
  });
}
