import { useMcpStore } from '@/entities/mcp/model/mcp.store';
import { fetchServers } from '@/shared/api/mcp';
import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';

export function useMcpServers() {
  const setServers = useMcpStore((state) => state.setServers);
  const servers = useMcpStore((state) => state.servers);

  const { data, isLoading } = useQuery({
    queryKey: ['mcp', 'servers'],
    queryFn: fetchServers,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  useEffect(() => {
    if (data) setServers(data);
  }, [data, setServers]);

  return { servers, isLoading };
}
