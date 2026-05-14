"""从 config.yaml 读取的 MCP 配置模型。"""

from pydantic import BaseModel, ConfigDict, Field

from deerflow.config.extensions_config import McpServerConfig


class NacosMcpConfig(BaseModel):
    """Nacos MCP Router 设置。"""

    enabled: bool = Field(default=True, description="是否自动注入 nacos-mcp-router")
    router_name: str = Field(default="nacos-mcp-router", description="注入的 MCP 服务名")
    username: str = Field(default="", description="可选：覆盖路由器环境变量中的 Nacos 用户名")
    password: str = Field(default="", description="可选：覆盖路由器环境变量中的 Nacos 密码")
    command: str = Field(default="uvx", description="路由器启动命令")
    args: list[str] = Field(default_factory=lambda: ["nacos-mcp-router@latest"], description="路由器启动参数")
    description: str = Field(default="Nacos MCP Router", description="注入路由器服务的描述")
    transport: str = Field(
        default="stdio",
        description="路由器传输方式：'stdio'（每次调用子进程）或 'streamable_http'（常驻 sidecar，推荐）",
    )
    port: int = Field(
        default=18000,
        description="当 transport=streamable_http 时 sidecar 使用的端口",
    )
    update_interval: int = Field(
        default=60,
        description="路由器内部 Nacos 刷新间隔（秒，对应 UPDATE_INTERVAL 环境变量）",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="传给路由器子进程的额外环境变量",
    )
    model_config = ConfigDict(extra="allow")


class NacosConfig(BaseModel):
    """Nacos 连接设置。"""

    server_addr: str = Field(default="127.0.0.1:8848", alias="server-addr", description="Nacos 服务地址")
    username: str = Field(default="nacos", description="Nacos 用户名")
    password: str = Field(default="", description="Nacos 密码")
    namespace: str = Field(default="public", description="Nacos 命名空间 ID")
    mcp: NacosMcpConfig = Field(default_factory=NacosMcpConfig, description="Nacos MCP Router 设置")
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class McpConfig(BaseModel):
    """config.yaml 中静态 MCP 服务配置。"""

    static_servers: dict[str, McpServerConfig] = Field(default_factory=dict, description="静态 MCP 服务列表")
    model_config = ConfigDict(extra="allow")
