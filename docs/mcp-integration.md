# MCP 集成指南

## MCP 简介

MCP (Model Context Protocol) 是一种标准化协议，用于连接 LLM Agent 与外部工具和服务。通过 MCP，Agent 可以访问文件系统、Git、数据库、API 等外部资源。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Loop Manager                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              LangChain Tools (统一接口)                    │  │
│  │  ├─ Skill Scripts (Python)                              │  │
│  │  ├─ LangChain Tools (built-in)                           │  │
│  │  └─ MCP Tools (external) ← MCP Integration               │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Client Pool                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Filesystem   │  │     Git      │  │   Postgres   │          │
│  │   Server     │  │   Server     │  │   Server     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                    │
│         └─────────────────┴─────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Tool Adapter                              │
│              MCP Tools → LangChain StructuredTools              │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 配置 MCP Servers

编辑 `config/mcp_servers.yaml`：

```yaml
servers:
  filesystem:
    type: stdio
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/path/to/your/project"
    enabled: true

  git:
    type: stdio
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-git"
      - "/path/to/your/repo"
    enabled: false  # 默认禁用
```

### 2. 初始化 MCP Manager

```python
from mcp.server_manager import get_mcp_manager

# 初始化 MCP Manager
mcp_manager = await get_mcp_manager(
    config_path="config/mcp_servers.yaml"
)
```

### 3. 集成到 Agent Manager

```python
from core.agent_manager import AgentLoopManager

# 创建 Agent Manager（包含 MCP 支持）
agent_manager = AgentLoopManager(
    llm=llm,
    skill_registry=skill_registry,
    mcp_server_manager=mcp_manager,
    checkpointer=checkpointer
)

# 注册 Agent（自动获取 MCP 工具）
agent = agent_manager.register_agent("my_agent")
```

### 4. 使用 MCP 工具

```python
# Agent 执行时，LLM 可以使用 MCP 工具
result = await agent.ainvoke({
    "messages": [HumanMessage(content="Read the README file")]
})

# LLM 会自动选择并调用 filesystem_read_file MCP 工具
```

## 配置详解

### Server 配置字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `type` | string | ✅ | 传输类型（目前只支持 `stdio`） |
| `command` | string | ✅ | 启动命令（如 `npx`, `python`） |
| `args` | list | ✅ | 命令参数 |
| `enabled` | boolean | ❌ | 是否启用（默认 false） |

### 常见 MCP Servers

#### 1. Filesystem Server

```yaml
filesystem:
  type: stdio
  command: npx
  args:
    - "-y"
    - "@modelcontextprotocol/server-filesystem"
    - "/Users/photon/dev/git/agent-loop"
  enabled: true
```

**提供的工具**:
- `filesystem_read_file`: 读取文件
- `filesystem_write_file`: 写入文件
- `filesystem_list_directory`: 列出目录
- `filesystem_delete_file`: 删除文件

#### 2. Git Server

```yaml
git:
  type: stdio
  command: npx
  args:
    - "-y"
    - "@modelcontextprotocol/server-git"
    - "/path/to/repo"
  enabled: true
```

**提供的工具**:
- `git_status`: Git 状态
- `git_diff`: Git diff
- `git_log`: Git 日志
- `git_checkout`: Git checkout

#### 3. PostgreSQL Server

```yaml
postgres:
  type: stdio
  command: npx
  args:
    - "-y"
    - "@modelcontextprotocol/server-postgres"
    - "postgresql://user:pass@localhost:5432/db"
  enabled: true
```

**提供的工具**:
- `postgres_query`: 执行 SQL 查询
- `postgres_describe`: 描述表结构

#### 4. Brave Search Server

```yaml
brave-search:
  type: stdio
  command: npx
  args:
    - "-y"
    - "@modelcontextprotocol/server-brave-search"
  enabled: true
```

**提供的工具**:
- `brave_search`: Web 搜索

## API 使用

### MCP Client Pool

```python
from mcp.client_pool import MCPClientPool

# 创建连接池
pool = MCPClientPool()

# 初始化服务器
servers_config = {
    "filesystem": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
        "enabled": True
    }
}

await pool.initialize(servers_config)

# 获取所有工具
tools = pool.get_all_tools()
print(f"Available tools: {[t['name'] for t in tools]}")

# 调用工具
result = await pool.call_tool("filesystem_read_file", {"path": "/tmp/file.txt"})
print(result)

# 关闭连接
await pool.close()
```

### MCP Tool Adapter

```python
from mcp.tool_adapter import MCPToolAdapter

# 创建适配器
adapter = MCPToolAdapter(pool)

# 转换所有工具
langchain_tools = adapter.convert_all_tools()

# 按名称过滤
specific_tools = adapter.filter_tools_by_names([
    "filesystem_read_file",
    "filesystem_write_file"
])

# 按服务器过滤
git_tools = adapter.filter_tools_by_server("git")
```

### MCP Server Manager

```python
from mcp.server_manager import MCPServerManager

# 创建管理器
manager = MCPServerManager()

# 初始化
await manager.initialize(config=servers_config)

# 获取所有工具
all_tools = manager.get_all_tools()

# 列出服务器
servers = manager.list_servers()
print(f"Connected servers: {servers}")

# 获取工具元数据
metadata = manager.list_tools_metadata()

# 重载服务器
success = await manager.reload_server("filesystem")

# 关闭管理器
await manager.close()
```

### 全局单例

```python
from mcp.server_manager import get_mcp_manager, reset_mcp_manager

# 获取全局实例
mcp_manager = await get_mcp_manager(
    config_path="config/mcp_servers.yaml"
)

# 使用管理器
tools = mcp_manager.get_all_tools()

# 重置（测试用）
reset_mcp_manager()
```

## 工具转换

### MCP Schema → Pydantic

MCP 使用 JSON Schema，LangChain 使用 Pydantic。适配器自动转换：

```python
# MCP Schema
{
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "File path"},
        "content": {"type": "string", "description": "File content"}
    },
    "required": ["path", "content"]
}

# 转换为 Pydantic
class FilesystemWriteFileInput(BaseModel):
    path: str = Field(description="File path")
    content: str = Field(description="File content")
```

### 类型映射

| MCP Type | Python Type |
|----------|-------------|
| string | `str` |
| integer | `int` |
| number | `float` |
| boolean | `bool` |
| array | `List[Any]` |
| object | `Dict[str, Any]` |

## Agent 集成

### 方法 1：通过 Agent Manager

```python
from core.agent_manager import AgentLoopManager
from mcp.server_manager import get_mcp_manager

# 初始化 MCP
mcp_manager = await get_mcp_manager(config_path="config/mcp_servers.yaml")

# 创建 Agent Manager
agent_manager = AgentLoopManager(
    llm=llm,
    skill_registry=skill_registry,
    mcp_server_manager=mcp_manager,
    checkpointer=checkpointer
)

# 注册 Agent（自动包含 MCP 工具）
agent = agent_manager.register_agent("my_agent")
```

### 方法 2：直接传递工具列表

```python
# 手动获取 MCP 工具
mcp_manager = await get_mcp_manager()
mcp_tools = mcp_manager.get_all_tools()

# 传递给 Agent Manager
agent_manager = AgentLoopManager(
    llm=llm,
    skill_registry=skill_registry,
    mcp_tools=mcp_tools  # 直接传递
)
```

## 高级用法

### 动态重载服务器

```python
# 重载单个服务器
success = await agent_manager.reload_mcp_server("filesystem")

if success:
    print("Server reloaded successfully")
    # Agent 自动重建
```

### 获取特定服务器的工具

```python
# 只获取 filesystem 工具
filesystem_tools = agent_manager.mcp_server_manager.get_tools_by_server("filesystem")

# 只获取 git 工具
git_tools = agent_manager.mcp_server_manager.get_tools_by_server("git")
```

### 直接调用 MCP 工具

```python
# 绕过 Agent，直接调用 MCP 工具
result = await mcp_manager.call_tool(
    "filesystem_read_file",
    {"path": "/tmp/README.md"}
)

print(result)
```

### 监控 MCP 连接

```python
# 检查连接状态
servers = mcp_manager.list_servers()
print(f"Connected servers: {servers}")

# 检查工具数量
tools_metadata = mcp_manager.list_tools_metadata()
print(f"Total tools: {len(tools_metadata)}")
```

## Skill 中使用 MCP Tools

### 1. 配置 allowed-tools

```yaml
---
name: file_analyzer
description: Analyze files and extract insights
allowed-tools: "filesystem_read_file, filesystem_list_directory"
version: 1.0.0
---

# File Analyzer Skill

## Instructions

1. List directory contents
2. Read relevant files
3. Analyze content
4. Generate report
```

### 2. Skill 自动使用 MCP 工具

当 Skill 被 LLM 调用时，系统会：
1. 解析 `allowed-tools`
2. 从 MCP 工具池中过滤工具
3. 绑定到 LLM
4. LLM 自动选择和调用

## 故障排查

### 问题 1：MCP Server 无法连接

**症状**：日志显示 "Failed to connect MCP server"

**解决方案**：
1. 检查 MCP Server 是否已安装
2. 验证 `command` 和 `args` 配置
3. 检查服务器路径权限
4. 查看 MCP Server 日志

### 问题 2：工具未被发现

**症状**：`get_all_tools()` 返回空列表

**解决方案**：
1. 检查 MCP Server 是否返回工具
2. 验证 `list_tools()` 调用
3. 检查工具命名规则
4. 查看 MCP Server 日志

### 问题 3：工具调用失败

**症状**：调用 MCP 工具时出错

**解决方案**：
1. 检查工具参数是否正确
2. 验证 MCP Server 状态
3. 检查连接超时设置
4. 查看详细错误日志

### 问题 4：内存泄漏

**症状**：长时间运行后内存增长

**解决方案**：
1. 定期调用 `await mcp_manager.close()`
2. 检查连接池大小
3. 监控 MCP Server 进程
4. 考虑使用连接池限制

## 最佳实践

### 1. 按需启用服务器

```yaml
filesystem:
  enabled: true   # 使用频繁，启用
git:
  enabled: false  # 偶尔使用，禁用
```

### 2. 合理配置连接池

```python
# 单个服务器的连接数
pool_size = 2
max_overflow = 5
```

### 3. 错误处理

```python
try:
    result = await mcp_manager.call_tool("tool_name", args)
except Exception as e:
    logger.error(f"MCP tool failed: {e}")
    # 降级处理
```

### 4. 监控和日志

```python
# 记录 MCP 调用
logger.info(
    "MCP tool call",
    extra={
        "tool_name": tool_name,
        "server_id": server_id,
        "args": args,
        "duration": duration
    }
)
```

### 5. 定期清理

```python
# 在应用关闭时
async def shutdown():
    await mcp_manager.close()
    await agent_manager.close()
```

## 性能优化

### 1. 连接池复用

```python
# 创建一次，重复使用
mcp_manager = await get_mcp_manager()

# 不要频繁创建和销毁
```

### 2. 工具缓存

```python
# 缓存工具列表
@lru_cache(maxsize=100)
def get_cached_tools():
    return mcp_manager.get_all_tools()
```

### 3. 并发连接

```python
# 并发连接多个服务器
await asyncio.gather(*[
    pool._connect_server(sid, config)
    for sid, config in servers_config.items()
])
```

### 4. 超时控制

```python
# 设置合理的超时
async with asyncio.timeout(30):
    result = await pool.call_tool(tool_name, args)
```

## 安全考虑

### 1. 路径隔离

```yaml
# 只暴露需要的目录
filesystem:
  args:
    - "/safe/directory"  # 不要暴露根目录
```

### 2. 工具权限

```yaml
# Skill 中限制工具
allowed-tools: "Read, Write"  # 不给 Bash 权限
```

### 3. 连接验证

```python
# 验证连接状态
if not mcp_manager.is_initialized:
    raise RuntimeError("MCP Manager not initialized")
```

### 4. 审计日志

```python
# 记录所有工具调用
logger.info(f"Tool called: {tool_name} by {user_id}")
```

## 示例：完整的 MCP 集成

```python
import asyncio
from mcp.server_manager import get_mcp_manager
from core.agent_manager import AgentLoopManager
from skills.registry import SkillRegistry
from storage.checkpoint import create_checkpoint_saver

async def main():
    # 1. 初始化 MCP
    mcp_manager = await get_mcp_manager(
        config_path="config/mcp_servers.yaml"
    )

    # 2. 初始化 Checkpoint
    checkpointer = create_checkpoint_saver(
        checkpoint_type="mysql",
        connection_string="mysql://root:pass@localhost:3306/agent_db"
    )

    # 3. 初始化 Skill Registry
    skill_registry = SkillRegistry(llm, [], "skills")

    # 4. 创建 Agent Manager
    agent_manager = AgentLoopManager(
        llm=llm,
        skill_registry=skill_registry,
        mcp_server_manager=mcp_manager,
        checkpointer=checkpointer
    )

    # 5. 注册 Agent
    agent = agent_manager.register_agent("my_agent")

    # 6. 执行任务
    result = await agent.ainvoke({
        "messages": [HumanMessage(content="Read and analyze the README file")]
    })

    print(result)

    # 7. 清理
    await mcp_manager.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

*文档版本：v1.0*
*最后更新：2026-02-07*