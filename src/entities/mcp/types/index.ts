export type McpTool = {
  id: string;
  name: string;
  description: string;
  command: string;
};

export type McpServer = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  latencyMs?: number;
  tools: McpTool[];
};
