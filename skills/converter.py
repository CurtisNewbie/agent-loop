"""SKILL.md → LangChain Tool 转换器"""
from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field
from skills.schemas import Skill


def skill_to_langchain_tool(
    skill: Skill,
    llm,
    mcp_tools: List[BaseTool]
) -> BaseTool:
    """
    将 SKILL.md 转换为 LangChain Tool（包含脚本工具）

    在 LangChain 中，Skill 本质上是一个包含提示逻辑的 Tool。
    当 LLM 调用这个 Tool 时，它会遵循 SKILL.md 中的指令。
    """

    # 定义输入参数
    class SkillInput(BaseModel):
        user_input: str = Field(description="用户请求或输入")

    # 创建 Tool 函数
    async def execute_skill(user_input: str) -> str:
        """
        执行 Skill：将 Skill 内容作为系统提示，使用允许的工具完成任务
        """
        # 1. 创建提示模板（Skill 内容作为系统消息）
        prompt = ChatPromptTemplate.from_messages([
            ("system", skill.content),
            ("user", user_input)
        ])

        # 2. 合并工具：脚本工具（自动发现） + MCP 工具
        all_available_tools = skill.script_tools + mcp_tools

        # 3. 根据 allowed-tools 过滤工具
        allowed_tool_names = skill.frontmatter.get_allowed_tools()
        if allowed_tool_names:
            # 只绑定允许的工具
            filtered_tools = [
                tool for tool in all_available_tools
                if tool.name in allowed_tool_names
            ]
        else:
            # 如果没有指定 allowed-tools，则使用所有可用工具
            filtered_tools = all_available_tools

        # 4. 绑定过滤后的工具到 LLM
        llm_with_tools = llm.bind_tools(filtered_tools)

        # 5. 创建执行链
        chain = prompt | llm_with_tools

        # 6. 执行（支持工具调用循环）
        messages = []
        for _ in range(10):  # 最多 10 次迭代
            response = await chain.ainvoke({"user_input": user_input})

            # 如果没有工具调用，返回结果
            tool_calls = getattr(response, 'tool_calls', None)
            if not tool_calls or not isinstance(tool_calls, (list, tuple)):
                return response.content

            # 执行工具调用
            for tool_call in tool_calls:
                tool = next((t for t in filtered_tools if t.name == tool_call["name"]), None)
                if tool:
                    result = await tool.ainvoke(tool_call["args"])
                    messages.append({
                        "role": "tool",
                        "content": str(result),
                        "tool_call_id": tool_call["id"]
                    })

        return "Skill execution completed"

    # 创建 LangChain StructuredTool
    langchain_skill = StructuredTool(
        name=skill.frontmatter.name,
        description=skill.frontmatter.description,
        args_schema=SkillInput,
        func=lambda user_input: execute_skill(user_input),
        coroutine=execute_skill
    )

    return langchain_skill