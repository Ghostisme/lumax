export interface MCPServerConfig extends Record<string, unknown> {
  enabled: boolean;
  description?: string;
  source?: "static" | "nacos";
  read_only?: boolean;
}

export interface MCPConfig {
  mcp_servers: Record<string, MCPServerConfig>;
}
