# API 参考文档

## 概述

Agent-Loop 服务提供 RESTful API，用于管理 Agent、对话、Skill 和 MCP 服务器。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API Version**: v1
- **Content-Type**: `application/json`

## 认证

所有 API 请求都需要认证：

```bash
# 使用 JWT Token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/agents/my_agent/chat
```

## Agent API

### 获取 Agent 列表

```http
GET /api/v1/agents
```

**响应**:
```json
{
  "agents": [
    {
      "id": "my_agent",
      "name": "My Agent",
      "description": "A helpful assistant",
      "version": "1.0.0",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### 获取 Agent 详情

```http
GET /api/v1/agents/{agent_id}
```

**参数**:
- `agent_id`: Agent 标识符

**响应**:
```json
{
  "id": "my_agent",
  "name": "My Agent",
  "description": "A helpful assistant",
  "llm": {
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "available_skills": ["code_review", "data_analysis"],
  "created_at": "2024-01-01T00:00:00Z"
}
```

## 对话 API

### 创建对话

```http
POST /api/v1/agents/{agent_id}/chat
```

**参数**:
- `agent_id`: Agent 标识符

**请求体**:
```json
{
  "conversation_id": "conv_123",
  "message": "Hello, how are you?",
  "metadata": {
    "user_id": "user_456"
  }
}
```

**响应**:
```json
{
  "conversation_id": "conv_123",
  "response": "I'm doing well, thank you!",
  "skill_used": null,
  "tools_called": [],
  "token_usage": {
    "prompt_tokens": 20,
    "completion_tokens": 15,
    "total_tokens": 35
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 流式对话

```http
POST /api/v1/agents/{agent_id}/stream
```

**请求体**:
```json
{
  "conversation_id": "conv_123",
  "message": "Tell me a joke"
}
```

**响应** (Server-Sent Events):
```
data: {"type": "token", "content": "Why"}
data: {"type": "token", "content": " did"}
data: {"type": "token", "content": " the"}
data: {"type": "token", "content": " chicken"}
data: {"type": "token", "content": " cross"}
data: {"type": "token", "content": " the"}
data: {"type": "token", "content": " road?"}
data: {"type": "done", "finish_reason": "stop"}
```

### 获取对话状态

```http
GET /api/v1/conversations/{conversation_id}/state
```

**响应**:
```json
{
  "conversation_id": "conv_123",
  "state": {
    "messages": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hi there!"}
    ],
    "current_skill": null,
    "step_count": 2
  },
  "checkpoint_info": {
    "thread_id": "conv_123",
    "checkpoint_ns": "",
    "last_updated": "2024-01-01T00:00:00Z"
  }
}
```

### 恢复对话

```http
POST /api/v1/conversations/{conversation_id}/resume
```

**请求体**:
```json
{
  "message": "Tell me more"
}
```

### 删除对话

```http
DELETE /api/v1/conversations/{conversation_id}
```

## Skill API

### 获取 Skill 列表

```http
GET /api/v1/skills
```

**响应**:
```json
{
  "skills": [
    {
      "id": "code_review",
      "name": "Code Review",
      "description": "Perform comprehensive code review",
      "version": "1.0.0",
      "allowed_tools": ["Read", "Write", "Bash"],
      "script_count": 2
    }
  ]
}
```

### 获取 Skill 详情

```http
GET /api/v1/skills/{skill_id}
```

**响应**:
```json
{
  "id": "code_review",
  "frontmatter": {
    "name": "code_review",
    "description": "Perform comprehensive code review",
    "allowed_tools": "Read, Write, Bash",
    "version": "1.0.0",
    "license": "MIT"
  },
  "content": "# Code Review Skill\n\n...",
  "scripts": [
    "linter.py",
    "security_check.py"
  ],
  "script_tools": [
    {
      "name": "code_review_linter",
      "description": "Run code linter"
    }
  ]
}
```

### 重载 Skill

```http
POST /api/v1/skills/{skill_id}/reload
```

**响应**:
```json
{
  "success": true,
  "message": "Skill 'code_review' reloaded successfully",
  "version": "1.0.1"
}
```

## MCP API

### 获取 MCP 服务器列表

```http
GET /api/v1/mcp/servers
```

**响应**:
```json
{
  "servers": [
    {
      "id": "filesystem",
      "type": "stdio",
      "status": "connected",
      "tool_count": 4,
      "last_error": null
    }
  ]
}
```

### 获取 MCP 工具列表

```http
GET /api/v1/mcp/tools
```

**查询参数**:
- `server_id`: 过滤特定服务器（可选）

**响应**:
```json
{
  "tools": [
    {
      "name": "filesystem_read_file",
      "description": "Read file from filesystem",
      "server_id": "filesystem",
      "input_schema": {
        "type": "object",
        "properties": {
          "path": {"type": "string"}
        }
      }
    }
  ]
}
```

### 重载 MCP 服务器

```http
POST /api/v1/mcp/servers/{server_id}/reload
```

**响应**:
```json
{
  "success": true,
  "message": "Server 'filesystem' reloaded successfully"
}
```

## 系统状态 API

### 健康检查

```http
GET /health
```

**响应**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z",
  "components": {
    "database": "ok",
    "redis": "ok",
    "mcp": "ok"
  }
}
```

### 指标

```http
GET /metrics
```

**响应** (Prometheus 格式):
```
# HELP
# TYPE agent_loop_requests_total counter
agent_loop_requests_total 1234

# TYPE agent_loop_duration_seconds histogram
agent_loop_duration_seconds_bucket{le="0.1"} 100
agent_loop_duration_seconds_bucket{le="1.0"} 500
agent_loop_duration_seconds_bucket{le="10.0"} 50

# TYPE agent_loop_active_conversations gauge
agent_loop_active_conversations 25
```

## 错误响应

所有 API 在出错时返回统一格式：

```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent 'unknown_agent' not found",
    "details": {
      "agent_id": "unknown_agent",
      "available_agents": ["my_agent", "code_review_agent"]
    }
  }
}
```

### 错误代码

| 代码 | 说明 |
|------|------|
| `AGENT_NOT_FOUND` | Agent 不存在 |
| `SKILL_NOT_FOUND` | Skill 不存在 |
| `CONVERSATION_NOT_FOUND` | 对话不存在 |
| `INVALID_REQUEST` | 请求参数无效 |
| `AUTHENTICATION_FAILED` | 认证失败 |
| `AUTHORIZATION_FAILED` | 权限不足 |
| `SERVER_ERROR` | 服务器内部错误 |
| `MCP_CONNECTION_FAILED` | MCP 连接失败 |

## 速率限制

所有 API 都有速率限制：

- **默认**: 100 请求/分钟
- **认证用户**: 1000 请求/分钟

超出限制时返回：

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded",
    "retry_after": 60
  }
}
```

## Webhook

### 对话完成 Webhook

配置 Webhook URL，在对话完成时接收通知：

```http
POST /api/v1/webhooks/conversation-complete
```

**请求体**:
```json
{
  "webhook_url": "https://your-server.com/callback",
  "events": ["conversation_complete"]
}
```

**Webhook Payload**:
```json
{
  "event": "conversation_complete",
  "conversation_id": "conv_123",
  "agent_id": "my_agent",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "message_count": 10,
    "token_usage": 500,
    "skills_used": ["code_review"]
  }
}
```

## 示例

### 示例 1: 简单对话

```bash
curl -X POST http://localhost:8000/api/v1/agents/my_agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test_conv",
    "message": "Hello!"
  }'
```

### 示例 2: 流式对话

```bash
curl -N -X POST http://localhost:8000/api/v1/agents/my_agent/stream \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test_conv",
    "message": "Tell me a story"
  }'
```

### 示例 3: 带 Skill 的对话

```bash
curl -X POST http://localhost:8000/api/v1/agents/my_agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "code_review_conv",
    "message": "Review the authentication module"
  }'
```

### 示例 4: 获取对话历史

```bash
curl http://localhost:8000/api/v1/conversations/test_conv/state
```

### 示例 5: 重载 Skill

```bash
curl -X POST http://localhost:8000/api/v1/skills/code_review/reload
```

## 版本控制

API 版本通过 URL 路径控制：

- `/api/v1/...` - v1 API（当前版本）
- 未来版本：`/api/v2/...`

### 向后兼容

在 v1 版本中：
- 字段添加是向后兼容的
- 字段移除会提前在 changelog 中说明
- 破坏性更改会通过 API version 处理

---

*文档版本：v1.0*
*最后更新：2026-02-07*