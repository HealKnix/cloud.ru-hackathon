import { useMcpStore } from '@/entities/mcp/model/mcp.store';
import { type McpTool } from '@/entities/mcp/types';
import { useMemo } from 'react';

export function useToolAutocomplete(rawQuery: string) {
  const servers = useMcpStore((state) => state.servers);
  const enabledServers = useMemo(
    () => servers.filter((s) => s.enabled),
    [servers],
  );

  const tools = useMemo(() => {
    const search = rawQuery.trim().toLowerCase();
    const allTools: (McpTool & { serverId: string; serverName: string })[] = [];
    enabledServers.forEach((server) => {
      server.tools.forEach((tool) =>
        allTools.push({
          ...tool,
          serverId: server.id,
          serverName: server.name,
        }),
      );
    });

    if (!search) return allTools;
    return allTools.filter(
      (tool) =>
        tool.command.toLowerCase().includes(search) ||
        tool.name.toLowerCase().includes(search) ||
        tool.description.toLowerCase().includes(search),
    );
  }, [rawQuery, enabledServers]);

  return { tools };
}
