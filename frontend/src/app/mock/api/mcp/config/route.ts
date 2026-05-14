export function GET() {
  return Response.json({
    mcp_servers: {
      "mcp-github-trending": {
        enabled: true,
        type: "stdio",
        command: "uvx",
        args: ["mcp-github-trending"],
        env: {},
        url: null,
        headers: {},
        description:
          "A MCP server that provides access to GitHub trending repositories and developers data",
        source: "static",
        read_only: false,
      },
      "context-7": {
        enabled: true,
        description:
          "Get the latest documentation and code into Cursor, Claude, or other LLMs",
        source: "nacos",
        read_only: true,
      },
      "feishu-importer": {
        enabled: true,
        description: "Import Feishu documents",
        source: "static",
        read_only: false,
      },
    },
  });
}
