"""Agent Loop 构建器 - 基于 LangGraph"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from skills.registry import SkillRegistry
from core.state import AgentState


class AgentGraphBuilder:
    """Agent Loop Graph 构建器"""

    def __init__(self, llm, skill_registry: SkillRegistry, mcp_tools: list, skill_tools: list = None):
        """
        Initialize Agent Graph Builder

        Args:
            llm: Language model instance
            skill_registry: Skill registry instance
            mcp_tools: List of MCP tools
            skill_tools: List of filtered Skill tools (LangChain Tools). If None, uses all skills.
        """
        self.llm = llm
        self.skill_registry = skill_registry
        self.mcp_tools = mcp_tools
        self.skill_tools = skill_tools if skill_tools is not None else skill_registry.get_all_langchain_tools()

    def build(self) -> StateGraph:
        """构建 Agent Loop StateGraph"""
        graph = StateGraph(AgentState)

        # 添加节点
        graph.add_node("classify_intent", self._classify_intent)
        graph.add_node("select_skill", self._select_skill)
        graph.add_node("execute_with_tools", self._execute_with_tools)
        graph.add_node("tools", ToolNode(self.mcp_tools))
        graph.add_node("format_result", self._format_result)

        # 定义边
        graph.set_entry_point("classify_intent")

        graph.add_conditional_edges(
            "classify_intent",
            self._should_use_skill,
            {
                "skill": "select_skill",
                "direct": "execute_with_tools"
            }
        )

        graph.add_edge("select_skill", "execute_with_tools")

        graph.add_conditional_edges(
            "execute_with_tools",
            self._should_call_tools,
            {
                "tools": "tools",
                "end": "format_result"
            }
        )

        graph.add_edge("tools", "execute_with_tools")
        graph.add_edge("format_result", END)

        return graph

    def _classify_intent(self, state: AgentState) -> Dict[str, Any]:
        """分类用户意图"""
        from langchain_core.prompts import MessagesPlaceholder

        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个意图分类器。请分析用户消息的意图。"),
            MessagesPlaceholder(variable_name="messages")
        ])

        chain = prompt | self.llm
        response = chain.invoke({"messages": state["messages"]})

        # 提取内容并确保是字符串
        content = ""
        if hasattr(response, 'content'):
            content = response.content
            if not isinstance(content, str):
                content = str(content)
        else:
            content = str(response)

        intent = content.strip().lower() if content else ""

        return {"intent": intent}

    def _select_skill(self, state: AgentState) -> Dict[str, Any]:
        """根据意图选择合适的 Skill（仅从可用的 skill_tools 中选择）"""
        intent = state["intent"]

        # 获取可用 skill_tools 对应的 Skill ID
        available_skill_ids = {tool.name for tool in self.skill_tools}
        available_skills = [skill for skill in self.skill_registry.list() if skill.id in available_skill_ids]

        # 简单匹配策略（实际可使用 LLM 选择）
        selected = None
        for skill in available_skills:
            skill_desc = skill.frontmatter.description.lower()
            if intent in skill_desc or skill_desc in intent:
                selected = skill.id
                break

        return {
            "current_skill": selected,
            "skill_status": "pending" if selected else None
        }

    def _execute_with_tools(self, state: AgentState) -> Dict[str, Any]:
        """LLM 使用工具（Skills + MCP Tools）执行任务"""
        from langchain_core.messages import AIMessage

        # 获取工具：过滤后的 Skill Tools + MCP Tools
        all_tools = self.skill_tools + self.mcp_tools

        # 绑定工具到 LLM
        llm_with_tools = self.llm.bind_tools(all_tools)

        # LLM 推理并执行
        response = llm_with_tools.invoke(state["messages"])

        # 确保返回 AIMessage
        if not isinstance(response, AIMessage):
            # 安全提取 content
            content = ""
            if hasattr(response, 'content'):
                content = response.content
                # 如果 content 仍然是 Mock 或其他对象，转换为字符串
                if not isinstance(content, (str, list)):
                    content = str(content)
            else:
                content = str(response)

            # 安全提取 tool_calls
            tool_calls = []
            if hasattr(response, 'tool_calls'):
                tc = response.tool_calls
                if tc is None:
                    tool_calls = []
                elif isinstance(tc, (list, tuple)):
                    # 确保列表中的每个元素也是有效的
                    tool_calls = [t for t in tc if t is not None]
                else:
                    tool_calls = []

            response = AIMessage(content=content, tool_calls=tool_calls)

        return {"messages": [response]}

    def _format_result(self, state: AgentState) -> Dict[str, Any]:
        """格式化最终结果"""
        last_message = state["messages"][-1]
        return {
            "messages": [
                AIMessage(
                    content=last_message.content,
                    additional_kwargs={
                        "intent": state["intent"],
                        "skill_used": state["current_skill"],
                        "skill_status": state["skill_status"]
                    }
                )
            ]
        }

    def _should_use_skill(self, state: AgentState) -> Literal["skill", "direct"]:
        """判断是否需要使用 Skill"""
        intent = state.get("intent", "")
        if not intent or not isinstance(intent, str):
            return "direct"
        skill_intents = ["code_review", "data_analysis", "file_operation"]
        return "skill" if any(skill in intent for skill in skill_intents) else "direct"

    def _should_call_tools(self, state: AgentState) -> Literal["tools", "end"]:
        """判断是否需要调用工具"""
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return "end"