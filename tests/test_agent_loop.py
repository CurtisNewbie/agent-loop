"""Agent Loop 测试"""
import pytest
from unittest.mock import Mock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import Runnable
from skills.registry import SkillRegistry
from core.agent_manager import AgentLoopManager
from core.state import AgentState
from storage.checkpoint import create_checkpoint_saver


class TestAgentLoopManager:
    """测试 Agent Loop Manager"""

    def test_register_agent(self):
        """测试注册 Agent"""
        # 创建 mock LLM
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # 创建 Skill Registry
        skill_registry = SkillRegistry(mock_llm, [], "skills")

        # 创建 Manager
        manager = AgentLoopManager(mock_llm, skill_registry, [])

        # 注册 Agent
        agent = manager.register_agent("test_agent")

        # 验证 Agent 已注册
        assert agent is not None
        assert manager.get_agent("test_agent") is not None

    def test_register_agent_with_checkpoint(self):
        """测试使用 Checkpoint 注册 Agent"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        skill_registry = SkillRegistry(mock_llm, [], "skills")
        checkpointer = create_checkpoint_saver("memory")

        manager = AgentLoopManager(mock_llm, skill_registry, [], checkpointer)
        agent = manager.register_agent("test_agent")

        assert agent is not None

    @pytest.mark.asyncio
    async def test_execute_agent(self):
        """测试执行 Agent"""
        # 创建 mock LLM
        from langchain_core.messages import AIMessage

        mock_llm = Mock()
        mock_response = AIMessage(content="Hello!", tool_calls=[])
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # 创建 Skill Registry
        skill_registry = SkillRegistry(mock_llm, [], "skills")

        # 创建 Manager
        manager = AgentLoopManager(mock_llm, skill_registry, [])
        agent = manager.register_agent("test_agent")

        # 初始状态
        initial_state = {
            "messages": [HumanMessage(content="Hello")],
            "intent": None,
            "current_skill": None,
            "skill_status": None,
            "intermediate_steps": [],
            "error": None,
            "metadata": {},
            "step_count": 0,
            "token_usage": {}
        }

        # 执行
        result = await agent.ainvoke(initial_state)

        # 验证结果
        assert result is not None
        assert len(result["messages"]) > 0

    @pytest.mark.asyncio
    async def test_agent_with_checkpoint_persistence(self):
        """测试 Agent Checkpoint 持久化"""
        from langchain_core.messages import AIMessage

        mock_llm = Mock()
        mock_response = AIMessage(content="Response", tool_calls=[])
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        skill_registry = SkillRegistry(mock_llm, [], "skills")
        checkpointer = create_checkpoint_saver("memory")

        manager = AgentLoopManager(mock_llm, skill_registry, [], checkpointer)
        agent = manager.register_agent("test_agent")

        config = {"configurable": {"thread_id": "test_thread"}}

        # 第一次执行
        initial_state = {
            "messages": [HumanMessage(content="First message")],
            "intent": None,
            "current_skill": None,
            "skill_status": None,
            "intermediate_steps": [],
            "error": None,
            "metadata": {},
            "step_count": 0,
            "token_usage": {}
        }
        result1 = await agent.ainvoke(initial_state, config)

        # 第二次执行（恢复状态）
        new_state = {
            "messages": [HumanMessage(content="Second message")]
        }
        result2 = await agent.ainvoke(new_state, config)

        # 验证结果
        assert result1 is not None
        assert result2 is not None
        # 消息历史应该累积
        assert len(result2["messages"]) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])