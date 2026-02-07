"""MCP Integration Tests - Real-world usage scenarios"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage
from skills.registry import SkillRegistry
from core.agent_manager import AgentLoopManager
from core.state import AgentState
from mcp.server_manager import MCPServerManager, reset_mcp_manager


class TestMCPIntegration:
    """Integration tests for MCP with Agent Loop"""

    @pytest.mark.asyncio
    async def test_mcp_manager_with_agent_manager(self):
        """Test MCP Manager integration with Agent Manager"""
        reset_mcp_manager()

        # Create mock LLM
        mock_llm = Mock()
        mock_response = AIMessage(content="Test response", tool_calls=[])
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.invoke = Mock(return_value=mock_response)
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # Initialize MCP Manager
        mcp_config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        mcp_manager = MCPServerManager()
        await mcp_manager.initialize(config=mcp_config)

        # Create Agent Manager with MCP
        skill_registry = SkillRegistry(mock_llm, [], "skills")
        agent_manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=skill_registry,
            mcp_server_manager=mcp_manager
        )

        # Register agent
        agent = agent_manager.register_agent("test_agent")

        # Verify agent was created
        assert agent is not None

        # Get MCP tools
        mcp_tools = agent_manager.get_mcp_tools()
        assert len(mcp_tools) > 0

        # Verify MCP tools are available
        tool_names = [tool.name for tool in mcp_tools]
        assert "filesystem_read_file" in tool_names

        # Cleanup
        await mcp_manager.close()
        reset_mcp_manager()

    @pytest.mark.asyncio
    async def test_agent_with_mcp_tools_execution(self):
        """Test agent execution with MCP tools"""
        reset_mcp_manager()

        # Create mock LLM
        mock_llm = Mock()
        mock_response = AIMessage(content="File read successfully", tool_calls=[])
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.invoke = Mock(return_value=mock_response)
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # Initialize MCP Manager
        mcp_config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        mcp_manager = MCPServerManager()
        await mcp_manager.initialize(config=mcp_config)

        # Create Agent Manager
        skill_registry = SkillRegistry(mock_llm, [], "skills")
        agent_manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=skill_registry,
            mcp_server_manager=mcp_manager
        )

        # Register agent
        agent = agent_manager.register_agent("test_agent")

        # Execute agent
        initial_state = {
            "messages": [HumanMessage(content="Read a file")],
            "intent": None,
            "current_skill": None,
            "skill_status": None,
            "intermediate_steps": [],
            "error": None,
            "metadata": {},
            "step_count": 0,
            "token_usage": {}
        }

        result = await agent.ainvoke(initial_state)

        # Verify execution
        assert result is not None
        assert len(result["messages"]) > 0

        # Verify LLM was called with MCP tools bound
        assert mock_llm.bind_tools.called

        # Cleanup
        await mcp_manager.close()
        reset_mcp_manager()

    @pytest.mark.asyncio
    async def test_mcp_server_reload(self):
        """Test MCP server reload functionality"""
        reset_mcp_manager()

        # Create mock LLM
        mock_llm = Mock()
        mock_response = AIMessage(content="Test", tool_calls=[])
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # Initialize MCP Manager
        mcp_config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        mcp_manager = MCPServerManager()
        await mcp_manager.initialize(config=mcp_config)

        # Create Agent Manager
        skill_registry = SkillRegistry(mock_llm, [], "skills")
        agent_manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=skill_registry,
            mcp_server_manager=mcp_manager
        )

        # Register agent
        agent = agent_manager.register_agent("test_agent")

        # Reload MCP server
        success = await agent_manager.reload_mcp_server("filesystem")
        assert success is True

        # Verify agent still works after reload
        result = await agent.ainvoke({
            "messages": [HumanMessage(content="Test")],
            "intent": None,
            "current_skill": None,
            "skill_status": None,
            "intermediate_steps": [],
            "error": None,
            "metadata": {},
            "step_count": 0,
            "token_usage": {}
        })

        assert result is not None

        # Cleanup
        await mcp_manager.close()
        reset_mcp_manager()

    @pytest.mark.asyncio
    async def test_multiple_mcp_servers(self):
        """Test agent with multiple MCP servers"""
        reset_mcp_manager()

        # Create mock LLM
        mock_llm = Mock()
        mock_response = AIMessage(content="Test", tool_calls=[])
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # Initialize MCP Manager with multiple servers
        mcp_config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                },
                "git": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-git", "/tmp"],
                    "enabled": True
                }
            }
        }

        mcp_manager = MCPServerManager()
        await mcp_manager.initialize(config=mcp_config)

        # Create Agent Manager
        skill_registry = SkillRegistry(mock_llm, [], "skills")
        agent_manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=skill_registry,
            mcp_server_manager=mcp_manager
        )

        # Register agent
        agent = agent_manager.register_agent("test_agent")

        # Get all MCP tools
        mcp_tools = agent_manager.get_mcp_tools()

        # Verify tools from both servers (mock adds prefix)
        tool_names = [tool.name for tool in mcp_tools]
        assert "filesystem_read_file" in tool_names
        assert "git_read_file" in tool_names  # Mock pattern

        # Verify we have tools from both servers
        filesystem_tools = [t for t in tool_names if t.startswith("filesystem_")]
        git_tools = [t for t in tool_names if t.startswith("git_")]
        assert len(filesystem_tools) > 0
        assert len(git_tools) > 0

        # Cleanup
        await mcp_manager.close()
        reset_mcp_manager()

    @pytest.mark.asyncio
    async def test_mcp_tool_direct_call(self):
        """Test direct MCP tool call through manager"""
        reset_mcp_manager()

        # Initialize MCP Manager
        mcp_config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        mcp_manager = MCPServerManager()
        await mcp_manager.initialize(config=mcp_config)

        # Call MCP tool directly
        result = await mcp_manager.call_tool("filesystem_read_file", {"path": "/tmp/test.txt"})

        # Verify result
        assert result is not None
        assert "Mock result" in result

        # Cleanup
        await mcp_manager.close()
        reset_mcp_manager()

    @pytest.mark.asyncio
    async def test_mcp_manager_lifecycle(self):
        """Test MCP Manager lifecycle (init, use, close)"""
        reset_mcp_manager()

        # Create manager
        mcp_manager = MCPServerManager()

        # Initialize
        mcp_config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }
        await mcp_manager.initialize(config=mcp_config)
        assert mcp_manager.is_initialized is True

        # Use
        tools = mcp_manager.get_all_tools()
        assert len(tools) > 0

        # List servers
        servers = mcp_manager.list_servers()
        assert "filesystem" in servers

        # Close
        await mcp_manager.close()
        assert mcp_manager.is_initialized is False

        reset_mcp_manager()

    @pytest.mark.asyncio
    async def test_backward_compatibility_with_mcp_tools_list(self):
        """Test backward compatibility with legacy mcp_tools parameter"""
        # Create mock LLM
        mock_llm = Mock()
        mock_response = AIMessage(content="Test", tool_calls=[])
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # Create Agent Manager with legacy parameter (empty list)
        skill_registry = SkillRegistry(mock_llm, [], "skills")
        agent_manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=skill_registry,
            mcp_tools=[]  # Empty list is valid
        )

        # Verify manager was created successfully
        assert agent_manager is not None
        assert agent_manager.mcp_server_manager is None
        assert agent_manager.mcp_tools == []

        # Register agent should work
        agent = agent_manager.register_agent("test_agent")
        assert agent is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])