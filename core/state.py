"""Agent 状态定义"""
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
from operator import add
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """Agent 状态定义 - 完全基于 LangGraph 语义"""

    # 消息历史（自动累积）
    messages: Annotated[List[BaseMessage], add]

    # 意图和路由
    intent: Optional[str]
    current_skill: Optional[str]

    # Skill 执行状态
    skill_status: Optional[Literal["pending", "running", "completed", "failed"]]

    # 中间结果（不持久化）
    intermediate_steps: List[Dict[str, Any]]

    # 错误信息
    error: Optional[str]

    # 元数据（不持久化到 checkpoint）
    metadata: Dict[str, Any]

    # 统计信息
    step_count: int
    token_usage: Dict[str, int]