# Skill 开发指南

## 什么是 Skill？

Skill 是可插拔、可配置的能力单元，定义了 Agent 如何执行特定任务。Skill 基于 **Claude Agent Skills** 格式，使用 Markdown 文件定义。

## Skill 结构

### 基本结构

```
skills/{skill_name}/
├── SKILL.md              # 必需：技能定义
├── scripts/              # 可选：Python 脚本工具
│   ├── linter.py
│   └── security_check.py
├── references/           # 可选：参考文档
│   └── coding_standards.md
└── assets/               # 可选：资源文件
    └── templates/
        └── report_template.txt
```

### SKILL.md 格式

```markdown
---
name: skill_name
description: Skill 功能描述（用于 LLM 匹配）
allowed-tools: "Tool1, Tool2, Tool3"
version: 1.0.0
license: MIT
---

# Skill Title

## Purpose
简短描述 Skill 的用途

## When to Use
- 使用场景 1
- 使用场景 2

## Instructions
详细的执行步骤

### Step 1: 准备
1. 步骤 1.1
2. 步骤 1.2

### Step 2: 执行
1. 步骤 2.1
2. 步骤 2.2

## Examples
使用示例

## Notes
注意事项和最佳实践
```

## Frontmatter 字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | Skill 唯一标识符 |
| `description` | string | ✅ | 功能描述（用于 LLM 匹配） |
| `allowed-tools` | string | ❌ | 允许使用的工具列表（逗号分隔） |
| `version` | string | ❌ | 版本号（默认 1.0.0） |
| `license` | string | ❌ | 许可证类型 |

## Skill 脚本

### 为什么需要脚本？

Skill 脚本提供项目特定的能力，作为 Python 函数实现，自动转换为 LangChain Tools。

### 脚本格式

**格式 1：使用 `@tool` 装饰器（推荐）**

```python
# skills/code_review/scripts/linter.py
from langchain.tools import tool
from pydantic import BaseModel, Field

class LinterInput(BaseModel):
    file_path: str = Field(description="要检查的文件路径")
    language: str = Field(default="python", description="编程语言")

@tool
def run_linter(file_path: str, language: str = "python") -> str:
    """
    运行代码风格检查器
    
    Args:
        file_path: 要检查的文件路径
        language: 编程语言
    
    Returns:
        检查结果
    """
    # 实现逻辑
    return f"Linting complete for {file_path}"
```

**格式 2：规范命名（自动发现）**

```python
# skills/code_review/scripts/security_check.py
def security_check_scan(file_path: str) -> str:
    """
    扫描文件的安全漏洞
    
    Args:
        file_path: 文件路径
    
    Returns:
        扫描结果
    """
    # 实现逻辑
    return f"Security scan complete for {file_path}"
```

### 脚本命名规则

- 文件名：`{tool_name}.py`
- 函数名：`{tool_name}` 或 `run_{tool_name}`
- 转换后的 Tool 名称：`{skill_name}_{script_name}_{function_name}`
- 示例：`code_review_linter_run_linter`

## 工具权限

### Allowed-Tools

控制 Skill 可以访问的工具：

```yaml
---
name: code_review
description: 代码审查
allowed-tools: "Read, Write, Bash"
---
```

**含义**：
- ✅ Skill 可以使用 `Read`, `Write`, `Bash` 工具
- ❌ Skill 不能使用其他工具（如 HTTP）

**安全优势**：
- 防止 Skill 访问敏感工具
- 最小权限原则
- 可审计的工具使用

### 工具类型

1. **Skill Scripts**: `skills/*/scripts/*.py`
2. **MCP Tools**: 通过 MCP Server 连接
3. **LangChain Tools**: `tools/*.py`

## Skill 开发示例

### 示例 1：简单的文本处理 Skill

```markdown
---
name: text_summarizer
description: Summarize long text into key points
version: 1.0.0
---

# Text Summarizer

## Purpose
Summarize long text into key points and main ideas.

## When to Use
- User provides a long article or document
- User asks for summary or key points
- User needs to extract main ideas

## Instructions

1. Read the provided text carefully
2. Identify the main topic and purpose
3. Extract key points (3-5 points)
4. Identify supporting details
5. Summarize in a clear, concise manner

## Notes
- Focus on the most important information
- Use bullet points for clarity
- Keep summaries under 200 words when possible
```

### 示例 2：带脚本的 Skill

```markdown
---
name: code_review
description: Perform comprehensive code review with security analysis
allowed-tools: "Read, Write, Bash"
version: 1.0.0
license: MIT
---

# Code Review Skill

## Purpose
Perform comprehensive code review including style checking, security analysis, and best practices verification.

## When to Use
- User asks to review code
- User mentions "code review", "check code", "analyze code"
- User wants to improve code quality

## Instructions

### Step 1: Understand the Code
1. Read the target file using the Read tool
2. Identify the programming language
3. Understand the code's purpose and structure

### Step 2: Style Review
Check for:
- Consistent indentation and formatting
- Naming conventions
- Comment quality and coverage
- Code organization

### Step 3: Security Review
Use the security_check tool to:
- Scan for SQL injection vulnerabilities
- Check for XSS risks
- Identify hardcoded secrets

### Step 4: Generate Report
Provide:
- Overall summary
- Critical issues (with line numbers)
- Suggestions for improvement
- Priority ranking of issues

## Notes
- Always provide line numbers for issues
- Suggest specific fixes, not just point out problems
- Be constructive and helpful
```

```python
# skills/code_review/scripts/linter.py
from langchain.tools import tool
from pydantic import BaseModel, Field

class LinterInput(BaseModel):
    file_path: str = Field(description="要检查的文件路径")
    language: str = Field(default="python", description="编程语言")

@tool
def run_linter(file_path: str, language: str = "python") -> str:
    """
    运行代码风格检查器
    
    Args:
        file_path: 要检查的文件路径
        language: 编程语言
    
    Returns:
        检查结果
    """
    # 实现简单的 linter 逻辑
    with open(file_path, 'r') as f:
        content = f.read()
    
    issues = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        if line.strip() and len(line) > 100:
            issues.append(f"Line {i}: Line too long (>100 chars)")
    
    if issues:
        return "\n".join(issues)
    else:
        return "No style issues found"
```

## Skill 测试

### 单元测试

```python
# tests/test_skills.py

def test_skill_loading():
    """测试 Skill 加载"""
    skill = SkillLoader.load("skills/code_review")
    assert skill.frontmatter.name == "code_review"
    assert len(skill.script_tools) > 0

def test_script_tool_execution():
    """测试脚本工具执行"""
    skill = SkillLoader.load("skills/code_review")
    linter_tool = skill.script_tools[0]
    
    result = linter_tool.func("/tmp/test.py")
    assert result is not None
```

### 集成测试

```python
async def test_skill_with_agent():
    """测试 Skill 与 Agent 集成"""
    skill_registry = SkillRegistry(llm, [], "skills")
    agent_manager = AgentLoopManager(llm, skill_registry, [])
    
    agent = agent_manager.register_agent("test_agent")
    result = await agent.ainvoke({
        "messages": [HumanMessage(content="Review this code")]
    })
    
    assert result is not None
```

## 最佳实践

### 1. 清晰的描述

```yaml
---
name: data_analyzer
description: Analyze data and generate insights from CSV/JSON files
---
```

✅ 好的描述：具体说明功能  
❌ 不好的描述：Analyze data

### 2. 合理的工具权限

```yaml
---
allowed-tools: "Read, Write"  # 只给需要的工具
---
```

✅ 最小权限原则  
❌ 过度授权

### 3. 结构化的指令

```markdown
## Instructions

### Step 1: 准备
1. 步骤 1.1
2. 步骤 1.2

### Step 2: 执行
1. 步骤 2.1
2. 步骤 2.2
```

✅ 清晰的步骤  
❌ 混乱的指令

### 4. 提供示例

```markdown
## Examples

### Example 1: Basic Usage
User: "Summarize this article"
You should:
1. Read the article
2. Extract key points
3. Summarize in 3-5 bullet points
```

✅ 有具体的示例  
❌ 只有抽象描述

### 5. 添加注意事项

```markdown
## Notes
- Always verify data integrity
- Handle missing values gracefully
- Consider data size limitations
```

✅ 边界情况说明  
❌ 假设一切正常

## 调试技巧

### 1. 查看 Skill 加载日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)

skill_registry = SkillRegistry(llm, [], "skills")
# 会打印 Skill 加载详情
```

### 2. 验证脚本工具

```python
skill = SkillLoader.load("skills/my_skill")
print(f"Loaded {len(skill.script_tools)} script tools")
for tool in skill.script_tools:
    print(f"  - {tool.name}: {tool.description}")
```

### 3. 测试单个 Skill

```python
# 创建测试 Agent
skill_registry = SkillRegistry(llm, [], "skills/my_skill")
agent_manager = AgentLoopManager(llm, skill_registry, [])
agent = agent_manager.register_agent("test")

# 测试执行
result = await agent.ainvoke({
    "messages": [HumanMessage(content="Test message")]
})
```

## 常见问题

### Q: Skill 没有被加载？

**A**: 检查以下几点：
1. SKILL.md 文件名是否正确
2. Frontmatter 格式是否正确
3. 文件编码是否为 UTF-8
4. 查看加载日志

### Q: 脚本工具没有被发现？

**A**: 确保以下条件：
1. 脚本文件在 `scripts/` 目录
2. 函数使用 `@tool` 装饰器或符合命名规范
3. 文件扩展名为 `.py`

### Q: LLM 没有使用我的 Skill？

**A**: 检查：
1. `description` 是否清晰
2. 是否与用户请求匹配
3. 是否有更匹配的 Skill

### Q: 工具调用失败？

**A**: 检查：
1. `allowed-tools` 是否包含该工具
2. 工具是否正确注册
3. 查看错误日志

## 进阶技巧

### 1. Skill 组合

```markdown
---
name: full_code_analysis
description: Complete code analysis with multiple tools
allowed-tools: "Read, Write, Bash, HTTP"
---
```

### 2. 动态参数

```python
@tool
def analyze_data(data_path: str, format: str = "csv") -> str:
    """分析数据文件"""
    # 根据 format 参数处理不同格式
    pass
```

### 3. 错误处理

```python
@tool
def risky_operation(input_data: str) -> str:
    """执行有风险的操作"""
    try:
        # 执行操作
        pass
    except Exception as e:
        return f"Error: {str(e)}"
```

### 4. 工具链

```python
@tool
def pipeline_step1(input_data: str) -> str:
    """管道步骤 1"""
    pass

@tool
def pipeline_step2(input_data: str) -> str:
    """管道步骤 2"""
    pass
```

---

*文档版本：v1.0*
*最后更新：2026-02-07*