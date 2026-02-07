"""Test LangChain tools integration."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from tools.shell_tool import shell_tool, execute_shell
from tools.file_tool import read_file_tool, write_file_tool, list_directory_tool, delete_file_tool
from tools.registry import ToolRegistry, get_all_tools


class TestShellTool:
    """Test shell tool."""
    
    def test_shell_tool_exists(self):
        """Test shell tool is created."""
        assert shell_tool.name == "bash"
        assert shell_tool.description
    
    def test_execute_simple_command(self):
        """Test executing a simple command."""
        result = execute_shell("echo 'hello'")
        assert "hello" in result
        assert "exit code: 0" in result
    
    def test_execute_with_timeout(self):
        """Test command timeout."""
        result = execute_shell("sleep 5", timeout=1)
        assert "timed out" in result.lower()
    
    def test_execute_invalid_command(self):
        """Test executing invalid command."""
        result = execute_shell("nonexistent_command_12345 2>&1")
        assert "not found" in result or "Error" in result


class TestHTTPTool:
    """Test HTTP tool."""
    
    def test_http_tool_exists(self):
        """Test HTTP tool is created."""
        from tools.http_tool import http_tool
        assert http_tool.name == "http_request"
        assert http_tool.description
    
    def test_http_get_request(self):
        """Test HTTP GET request."""
        import sys
        import importlib
        httpx_mock = MagicMock()
        sys.modules['httpx'] = httpx_mock
        
        from tools.http_tool import make_http_request_sync
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        
        httpx_mock.Client.return_value = mock_client
        
        result = make_http_request_sync("GET", "http://example.com")
        assert "status_code" in result
        assert "200" in result


class TestFileTool:
    """Test file system tools."""
    
    def test_file_tools_exist(self):
        """Test file tools are created."""
        assert read_file_tool.name == "read_file"
        assert write_file_tool.name == "write_file"
        assert list_directory_tool.name == "list_directory"
        assert delete_file_tool.name == "delete_file"
    
    def test_write_and_read_file(self, tmp_path):
        """Test writing and reading a file."""
        file_path = tmp_path / "test.txt"
        content = "Hello, World!"
        
        # Write
        write_result = write_file_tool.func(str(file_path), content)
        assert "Successfully" in write_result
        
        # Read
        read_result = read_file_tool.func(str(file_path))
        assert read_result == content
    
    def test_list_directory(self, tmp_path):
        """Test listing directory contents."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        
        result = list_directory_tool.func(str(tmp_path))
        assert "file1.txt" in result
        assert "file2.txt" in result
    
    def test_delete_file(self, tmp_path):
        """Test deleting a file."""
        file_path = tmp_path / "to_delete.txt"
        file_path.write_text("content")
        
        assert file_path.exists()
        
        result = delete_file_tool.func(str(file_path))
        assert "Successfully" in result
        assert not file_path.exists()


class TestToolRegistry:
    """Test tool registry."""
    
    def test_registry_initialization(self):
        """Test registry initializes with default tools."""
        registry = ToolRegistry()
        assert len(registry) > 0
    
    def test_get_all_tools(self):
        """Test getting all tools."""
        tools = get_all_tools()
        assert len(tools) > 0
        
        tool_names = [t.name for t in tools]
        assert "bash" in tool_names
        assert "http_request" in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
    
    def test_register_custom_tool(self):
        """Test registering a custom tool."""
        from tools.registry import ToolRegistry
        
        @tool(description="A custom test tool")
        def custom_tool_func(input: str) -> str:
            return f"custom: {input}"
        
        registry = ToolRegistry()
        initial_count = len(registry)
        
        registry.register(custom_tool_func)
        assert len(registry) == initial_count + 1
        assert "custom_tool_func" in registry.list_tools()
    
    def test_unregister_tool(self):
        """Test unregistering a tool."""
        from tools.registry import ToolRegistry
        
        @tool(description="A temporary test tool")
        def temp_tool_func(input: str) -> str:
            return "temp"
        
        registry = ToolRegistry()
        registry.register(temp_tool_func)
        
        assert "temp_tool_func" in registry
        registry.unregister("temp_tool_func")
        assert "temp_tool_func" not in registry


class TestToolIntegration:
    """Test tool integration with agent loop."""
    
    def test_tools_with_agent_manager(self):
        """Test tools work with agent manager."""
        from core.agent_manager import AgentLoopManager
        from skills.registry import SkillRegistry
        
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Done"))
        
        skill_registry = SkillRegistry(mock_llm, [], "skills")
        tools = get_all_tools()
        
        manager = AgentLoopManager(mock_llm, skill_registry, tools)
        agent = manager.register_agent("test_agent")
        
        assert agent is not None
    
    def test_tool_discovery_by_llm(self):
        """Test LLM can discover and use tools."""
        tools = get_all_tools()
        tool_names = [t.name for t in tools]
        
        # Verify core tools are available
        assert "bash" in tool_names
        assert "http_request" in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "list_directory" in tool_names
        assert "delete_file" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
