# Architecture Documentation

## System Architecture

The Agent-Loop service is built on a modular architecture with clear separation of concerns:

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                      │
│                 (请求路由、鉴权、限流、日志)                      │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Agent Loop Manager                            │
│              (管理多个 LangGraph 编译实例)                        │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ├─────────────────┬─────────────────┬─────────────────┐
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐
│  Agent Loop 1   │ │  Agent Loop 2   │ │  Agent Loop N   │ │   Dynamic    │
│  (StateGraph)   │ │  (StateGraph)   │ │  (StateGraph)   │ │   Router     │
│  - 编译后的图    │ │  - 编译后的图    │ │  - 编译后的图    │ │  (可选)      │
│  - Checkpointer │ │  - Checkpointer │ │  - Checkpointer │ │              │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └──────────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Skill Registry                              │
│  - Skill 加载器 (SKILL.md 解析)                                  │
│  - Skill 元数据管理 (YAML Frontmatter)                          │
│  - Skill 版本管理                                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Client Pool                              │
│  - MCP Server 连接管理                                          │
│  - 工具自动发现                                                  │
│  - MCP Tool → LangChain Tool 转换                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Checkpoint Storage                  │
│  - MySQL (主存储)                                                │
│  - PostgreSQL (可选)                                            │
│  - Redis (缓存)                                                  │
│  - Memory (开发测试)                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
User Request
    │
    ▼
┌─────────────┐
│  API Gateway │ → 验证请求，路由到 Agent
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  Agent Loop Manager │ → 获取或创建 Agent 实例
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  LangGraph Agent    │ → 执行 Agent StateGraph
└──────┬──────────────┘
       │
       ├─────────────┬──────────────┐
       │             │              │
       ▼             ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Skills  │  │ MCP Tools│  │   State  │
└──────────┘  └──────────┘  └──────────┘
       │             │              │
       └─────────────┴──────────────┘
                    │
                    ▼
            ┌───────────────┐
            │  Checkpoint    │ → 持久化状态
            └───────────────┘
```

## Core Components

### 1. Agent Loop Manager (`core/agent_manager.py`)

**Responsibilities**:
- 管理多个编译后的 LangGraph 实例
- Agent 生命周期管理（注册、获取、重载）
- 集成 MCP 工具
- Checkpoint 管理

**Key Methods**:
- `register_agent(agent_id)`: 注册并编译 Agent
- `get_agent(agent_id)`: 获取已编译的 Agent
- `reload_agent(agent_id)`: 热重载 Agent
- `reload_mcp_server(server_id)`: 重载 MCP 服务器

### 2. Skill System (`skills/`)

**Components**:
- `schemas.py`: Skill 数据模型
- `loader.py`: SKILL.md 加载器和脚本工具加载
- `converter.py`: Skill → LangChain Tool 转换器
- `registry.py`: Skill 注册中心

**Skill Structure**:
```
skills/{skill_name}/
├── SKILL.md              # 技能定义（YAML Frontmatter + Markdown）
├── scripts/              # 可选：Python 脚本工具
│   ├── linter.py
│   └── security_check.py
├── references/           # 可选：参考文档
└── assets/               # 可选：资源文件
```

### 3. MCP Integration (`mcp/`)

**Components**:
- `client_pool.py`: MCP 客户端连接池
- `tool_adapter.py`: MCP → LangChain 工具转换
- `server_manager.py`: MCP 服务器生命周期管理

**Features**:
- 多服务器并发连接
- 工具自动发现
- 动态工具转换
- 服务器热重载

### 4. Checkpoint Storage (`storage/`)

**Implementations**:
- `checkpoint.py`: 工厂模式创建 Checkpoint Saver
- `mysql_checkpoint.py`: MySQL 实现（主存储）
- `postgres_checkpoint.py`: PostgreSQL 实现（可选）
- `redis_checkpoint.py`: Redis 实现（缓存）
- `memory_checkpoint.py`: 内存实现（开发测试）

**Isolation Strategy**:
```python
config = {
    "configurable": {
        "thread_id": f"{tenant_id}:{user_id}:{conversation_id}",
        "checkpoint_ns": tenant_id  # 命名空间隔离
    }
}
```

## Data Flow

### Agent Execution Flow

```
1. 用户请求 → API Gateway
2. 路由 → Agent Loop Manager
3. 获取 Agent → 已编译的 LangGraph
4. 初始状态 → {messages: [HumanMessage], ...}
5. 执行 Graph:
   - classify_intent → 意图分类
   - select_skill → 选择 Skill（如需要）
   - execute_with_tools → LLM + 工具执行
   - format_result → 格式化输出
6. 状态保存 → Checkpoint
7. 返回结果 → API Gateway → 用户
```

### Skill Execution Flow

```
1. LLM 选择 Skill
2. 加载 SKILL.md 内容
3. 解析 allowed-tools
4. 过滤可用工具（Skills + MCP Tools）
5. 绑定工具到 LLM
6. LLM 执行任务（使用 SKILL.md 指令）
7. 返回结果
```

### MCP Tool Execution Flow

```
1. Agent Manager 获取 MCP 工具
2. LLM 绑定工具
3. LLM 调用工具
4. Tool Adapter 转换调用
5. MCP Client Pool 路由到 MCP Server
6. MCP Server 执行
7. 返回结果 → LLM
```

## State Management

### AgentState Structure

```python
class AgentState(TypedDict):
    # 消息历史（自动累积）
    messages: Annotated[List[BaseMessage], add]
    
    # 意图和路由
    intent: Optional[str]
    current_skill: Optional[str]
    
    # Skill 执行状态
    skill_status: Optional[Literal["pending", "running", "completed", "failed"]]
    
    # 中间结果
    intermediate_steps: List[Dict[str, Any]]
    
    # 错误信息
    error: Optional[str]
    
    # 元数据
    metadata: Dict[str, Any]
    
    # 统计信息
    step_count: int
    token_usage: Dict[str, int]
```

### Checkpoint Persistence

**Thread-based Isolation**:
- 每个会话使用唯一的 `thread_id`
- 不同会话的状态完全隔离
- 支持断点续传

**Namespace-based Isolation**:
- 使用 `checkpoint_ns` 实现租户隔离
- 多租户环境下安全隔离

**Supported Backends**:
- MySQL: 生产环境主存储
- PostgreSQL: 备选方案
- Redis: 高性能缓存
- Memory: 开发测试

## Tool System

### Tool Types

1. **Skill Scripts** (`skills/*/scripts/*.py`)
   - 项目特定逻辑
   - Python 函数，带 `@tool` 装饰器
   - 同进程执行

2. **MCP Tools** (通过 MCP Server)
   - 外部服务集成
   - 独立进程执行
   - 天然隔离

3. **LangChain Tools** (`tools/*.py`)
   - Shell、HTTP、File 操作
   - 基础工具集

### Tool Discovery

```
┌─────────────────────────────────────┐
│      Tool Discovery Process         │
└─────────────────────────────────────┘
              │
              ├─► Skill Scripts
              │    ├── skills/*/scripts/*.py
              │    └── 动态导入 + 转换
              │
              ├─► MCP Tools
              │    ├── MCP Servers
              │    └── stdio → JSON-RPC
              │
              └─► LangChain Tools
                   └── tools/*.py
```

### Tool Binding

```python
# 获取所有可用工具
all_tools = skill_tools + mcp_tools + langchain_tools

# LLM 绑定工具
llm_with_tools = llm.bind_tools(all_tools)

# LLM 自动选择和调用
response = llm_with_tools.invoke(messages)
```

## Concurrency Model

### Multi-Request Handling

```
Single Pod (Shared Process)
    │
    ├─► Request 1 → thread_id: "req_001" → Workspace: /tmp/work/req_001/
    │
    ├─► Request 2 → thread_id: "req_002" → Workspace: /tmp/work/req_002/
    │
    ├─► Request N → thread_id: "req_00N" → Workspace: /tmp/work/req_00N/
    │
    └─► LangGraph CompiledGraph (共享)
        ├── StateGraph (共享)
        └── Checkpoint Saver (共享)
            └── PostgreSQL/MySQL (共享)
```

### Isolation Levels

1. **State Isolation**: LangGraph Checkpoint (thread_id)
2. **Filesystem Isolation**: Workspace Manager (per request)
3. **Tool Isolation**: MCP Server (separate process)
4. **Connection Isolation**: Connection pooling

## Error Handling

### Error Recovery Strategy

1. **Skill Execution Error**
   - 记录错误到 `error` 字段
   - 返回友好错误消息
   - 不中断 Agent 执行

2. **MCP Server Error**
   - 自动重试（可配置）
   - 超时机制
   - 降级到备用服务器

3. **Checkpoint Error**
   - 记录警告
   - 继续执行（非持久化模式）
   - 管理员告警

### Logging Strategy

```python
# 结构化日志
logger.info(
    "Agent execution",
    extra={
        "agent_id": agent_id,
        "conversation_id": conversation_id,
        "skill_used": skill_id,
        "tool_calls": len(tool_calls),
        "tokens_used": token_count
    }
)
```

## Security Considerations

### Tool Permission Control

**Allowed-Tools Mechanism**:
```yaml
# SKILL.md
---
name: code_review
allowed-tools: "Read, Write, Bash"
---
```

**Implementation**:
```python
allowed_tools = skill.frontmatter.get_allowed_tools()
filtered_tools = [t for t in all_tools if t.name in allowed_tools]
```

### Workspace Isolation

**Path Traversal Prevention**:
```python
def safe_path(request_id: str, file_path: str) -> Path:
    workspace = get_workspace(request_id)
    full_path = (workspace / file_path).resolve()
    
    if not full_path.is_relative_to(workspace.resolve()):
        raise PermissionError("Access denied")
    
    return full_path
```

### MCP Server Security

- stdio 传输层隔离
- 连接池管理
- 超时控制
- 资源限制

## Performance Optimization

### Connection Pooling

**MySQL/PostgreSQL**:
```python
pool_size = 5
max_overflow = 10
```

**MCP Clients**:
```python
# 每个 Server 一个连接池
pool_size = 2
max_overflow = 5
```

### Caching Strategy

```
┌─────────────────────────────────────┐
│         Caching Layers              │
└─────────────────────────────────────┘
    L1: Agent Instance (Memory)
    L2: Skill Registry (Memory)
    L3: MCP Tools (Memory)
    L4: Checkpoint (Redis)
    L5: Database (MySQL/PostgreSQL)
```

### Async Operations

- 所有 I/O 操作异步化
- 并发连接池
- 非阻塞工具执行

## Scalability

### Horizontal Scaling

```
API Gateway (Load Balanced)
    │
    ├─► Pod 1 (Agent Manager)
    │    ├─► Agent Loop 1
    │    ├─► Agent Loop 2
    │    └─► Shared Database
    │
    ├─► Pod 2 (Agent Manager)
    │    ├─► Agent Loop 3
    │    ├─► Agent Loop 4
    │    └─► Shared Database
    │
    └─► Pod N (Agent Manager)
```

### Database Scaling

- Read replicas for Checkpoint reads
- Connection pooling
- Query optimization

---

*文档版本：v1.0*
*最后更新：2026-02-07*