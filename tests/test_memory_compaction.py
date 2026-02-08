"""Tests for Memory Compaction functionality"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from core.memory_compactor import MemoryCompactor, CompactionStrategy, create_memory_compactor


class TestMemoryCompactor:
    """Test MemoryCompactor class"""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM"""
        llm = Mock()
        llm.model_name = "claude-3-5-sonnet"
        return llm

    @pytest.fixture
    def compactor(self, mock_llm):
        """Create a MemoryCompactor instance"""
        return MemoryCompactor(
            llm=mock_llm,
            strategy=CompactionStrategy.TOKEN_AWARE,
            max_tokens=1000,
            max_messages=5,
            keep_system_message=True,
            keep_last_n_messages=3,
        )

    def test_estimate_context_window(self, mock_llm):
        """Test context window estimation for different models"""
        # Test with claude-3-5-sonnet
        mock_llm.model_name = "claude-3-5-sonnet"
        mock_llm.model = ""
        compactor = MemoryCompactor(llm=mock_llm)
        # The max_tokens is set during init when None is provided
        assert compactor.max_tokens == 200000

        # Test with gpt-4o (create new compactor to trigger re-estimation)
        mock_llm.model_name = "gpt-4o"
        compactor2 = MemoryCompactor(llm=mock_llm)
        assert compactor2.max_tokens == 128000

        # Test with unknown model
        mock_llm.model_name = "unknown-model"
        compactor3 = MemoryCompactor(llm=mock_llm)
        assert compactor3.max_tokens == 8000  # Default

    def test_count_tokens(self, compactor):
        """Test token counting"""
        messages = [
            HumanMessage(content="Hello world"),
            AIMessage(content="Hi there!"),
        ]

        token_count = compactor.count_tokens(messages)
        assert token_count > 0
        # Rough estimate: ~10 chars / 4 ≈ 2-3 tokens per message
        assert token_count < 100

    def test_trim_messages_no_compaction_needed(self, compactor):
        """Test that messages are not trimmed when within limits"""
        messages = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi"),
        ]

        result = compactor.trim_messages(messages)
        assert len(result) == len(messages)
        assert result == messages

    def test_trim_sliding_window(self, compactor):
        """Test sliding window compaction"""
        messages = [SystemMessage(content="System instruction")]
        messages.extend([HumanMessage(content=f"Message {i}") for i in range(10)])

        compactor.strategy = CompactionStrategy.SLIDING_WINDOW
        compactor.max_messages = 5

        result = compactor._trim_sliding_window(messages)

        # Should keep system message + last 5 messages
        assert len(result) <= 6  # System + 5 messages
        assert any(isinstance(m, SystemMessage) for m in result)

    def test_trim_sliding_window_no_system(self, compactor):
        """Test sliding window without keeping system messages"""
        messages = [SystemMessage(content="System instruction")]
        messages.extend([HumanMessage(content=f"Message {i}") for i in range(10)])

        compactor.strategy = CompactionStrategy.SLIDING_WINDOW
        compactor.max_messages = 5
        compactor.keep_system_message = False

        result = compactor._trim_sliding_window(messages)

        # Should keep only last 5 messages
        assert len(result) == 5
        assert not any(isinstance(m, SystemMessage) for m in result)

    def test_trim_token_aware(self, compactor):
        """Test token-aware compaction"""
        # Create messages that exceed the token limit
        messages = [
            SystemMessage(content="System instruction"),
        ]
        for i in range(20):
            messages.append(HumanMessage(content=f"Message {i} " * 100))  # Long messages

        compactor.strategy = CompactionStrategy.TOKEN_AWARE
        compactor.max_tokens = 500
        compactor.keep_last_n_messages = 3

        result = compactor._trim_token_aware(messages)

        # Should keep system message and some middle messages + last 3
        assert len(result) < len(messages)
        assert any(isinstance(m, SystemMessage) for m in result)

    def test_trim_hybrid(self, compactor):
        """Test hybrid compaction"""
        messages = [SystemMessage(content="System instruction")]
        messages.extend([HumanMessage(content=f"Message {i}") for i in range(15)])

        compactor.strategy = CompactionStrategy.HYBRID
        compactor.max_messages = 5
        compactor.max_tokens = 500

        result = compactor._trim_hybrid(messages)

        # Should be significantly trimmed
        assert len(result) < len(messages)

    def test_get_compaction_info(self, compactor):
        """Test getting compaction statistics"""
        messages = [
            SystemMessage(content="System instruction"),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi"),
            ToolMessage(content="Tool result", tool_call_id="123"),
        ]

        info = compactor.get_compaction_info(messages)

        assert info["total_messages"] == 4
        assert info["total_tokens"] > 0
        assert info["max_tokens"] == 1000
        assert info["message_breakdown"]["system"] == 1
        assert info["message_breakdown"]["human"] == 1
        assert info["message_breakdown"]["ai"] == 1
        assert info["message_breakdown"]["tool"] == 1
        assert info["strategy"] == "token_aware"

    def test_get_compaction_info_needs_compaction(self, compactor):
        """Test compaction info detection when compaction is needed"""
        messages = [HumanMessage(content="X" * 10000) for _ in range(10)]

        compactor.max_tokens = 100

        info = compactor.get_compaction_info(messages)

        assert info["needs_compaction"] is True
        assert info["token_usage_ratio"] > 1.0

    


class TestCreateMemoryCompactor:
    """Test create_memory_compactor factory function"""

    def test_create_with_defaults(self):
        """Test creating compactor with default settings"""
        mock_llm = Mock()
        mock_llm.model_name = "claude-3-5-sonnet"

        compactor = create_memory_compactor(mock_llm)

        assert compactor.strategy == CompactionStrategy.TOKEN_AWARE
        assert compactor.keep_system_message is True
        assert compactor.keep_last_n_messages == 10

    def test_create_with_custom_settings(self):
        """Test creating compactor with custom settings"""
        mock_llm = Mock()
        mock_llm.model_name = "claude-3-5-sonnet"

        compactor = create_memory_compactor(
            mock_llm,
            strategy="sliding_window",
            max_tokens=5000,
            max_messages=20,
            keep_system_message=False,
            keep_last_n_messages=5,
        )

        assert compactor.strategy == CompactionStrategy.SLIDING_WINDOW
        assert compactor.max_tokens == 5000
        assert compactor.max_messages == 20
        assert compactor.keep_system_message is False
        assert compactor.keep_last_n_messages == 5

    def test_create_with_all_strategies(self):
        """Test creating compactors with all strategies"""
        mock_llm = Mock()
        mock_llm.model_name = "claude-3-5-sonnet"

        strategies = ["sliding_window", "token_aware", "summary", "hybrid"]

        for strategy in strategies:
            compactor = create_memory_compactor(mock_llm, strategy=strategy)
            assert compactor.strategy.value == strategy


class TestMemoryCompactionIntegration:
    """Integration tests for memory compaction with agent loop"""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM"""
        llm = Mock()
        llm.model_name = "claude-3-5-sonnet"
        llm.bind_tools = Mock(return_value=llm)
        llm.invoke = Mock()
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.tool_calls = []
        llm.invoke.return_value = mock_response
        return llm

    @pytest.fixture
    def mock_skill_registry(self):
        """Create a mock skill registry"""
        registry = Mock()
        registry.get_all_langchain_tools = Mock(return_value=[])
        return registry

    def test_agent_graph_builder_with_compaction(self, mock_llm, mock_skill_registry):
        """Test AgentGraphBuilder with memory compaction enabled"""
        from core.agent_graph import AgentGraphBuilder
        from core.memory_compactor import create_memory_compactor

        memory_compactor = create_memory_compactor(mock_llm, max_tokens=1000)

        builder = AgentGraphBuilder(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            mcp_tools=[],
            skill_tools=[],
            enable_memory_compaction=True,
            memory_compactor=memory_compactor,
        )

        assert builder.enable_memory_compaction is True
        assert builder.memory_compactor is not None

    def test_agent_graph_builder_without_compaction(self, mock_llm, mock_skill_registry):
        """Test AgentGraphBuilder without memory compaction"""
        from core.agent_graph import AgentGraphBuilder

        builder = AgentGraphBuilder(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            mcp_tools=[],
            skill_tools=[],
            enable_memory_compaction=False,
        )

        assert builder.enable_memory_compaction is False
        assert builder.memory_compactor is None

    def test_agent_manager_with_compaction(self, mock_llm, mock_skill_registry):
        """Test AgentLoopManager with memory compaction enabled"""
        from core.agent_manager import AgentLoopManager

        manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            enable_memory_compaction=True,
            memory_compaction_strategy="token_aware",
            memory_compaction_max_tokens=1000,
        )

        assert manager.enable_memory_compaction is True
        assert manager.memory_compaction_strategy == "token_aware"
        assert manager.memory_compaction_max_tokens == 1000

    def test_agent_manager_register_agent_with_compaction(self, mock_llm, mock_skill_registry):
        """Test registering an agent with memory compaction settings"""
        from core.agent_manager import AgentLoopManager

        manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
            enable_memory_compaction=False,  # Global: disabled
        )

        # Register agent with compaction enabled (override)
        agent = manager.register_agent(
            agent_id="test_agent",
            enable_memory_compaction=True,
            memory_compaction_strategy="sliding_window",
            memory_compaction_max_messages=5,
        )

        assert agent is not None
        config = manager.agent_configs["test_agent"]
        assert config["enable_memory_compaction"] is True
        assert config["memory_compaction_strategy"] == "sliding_window"
        assert config["memory_compaction_max_messages"] == 5

    def test_agent_manager_reload_agent_preserves_compaction(self, mock_llm, mock_skill_registry):
        """Test that reloading an agent preserves memory compaction settings"""
        from core.agent_manager import AgentLoopManager

        manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=mock_skill_registry,
        )

        # Register agent with compaction
        agent = manager.register_agent(
            agent_id="test_agent",
            enable_memory_compaction=True,
            memory_compaction_strategy="token_aware",
            memory_compaction_max_tokens=2000,
        )

        # Reload agent
        reloaded = manager.reload_agent("test_agent")

        assert reloaded is not None
        config = manager.agent_configs["test_agent"]
        assert config["enable_memory_compaction"] is True
        assert config["memory_compaction_strategy"] == "token_aware"
        assert config["memory_compaction_max_tokens"] == 2000