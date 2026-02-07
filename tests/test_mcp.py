"""MCP Tests"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from mcp.client_pool import MCPClientPool
from mcp.tool_adapter import MCPToolAdapter
from mcp.server_manager import MCPServerManager, get_mcp_manager, reset_mcp_manager


class TestMCPClientPool:
    """Test MCP Client Pool"""

    @pytest.mark.asyncio
    async def test_create_pool(self):
        """Test creating MCP client pool"""
        pool = MCPClientPool()
        assert pool is not None
        assert pool.clients == {}
        assert pool.tools == {}

    @pytest.mark.asyncio
    async def test_initialize_empty_config(self):
        """Test initialization with empty config"""
        pool = MCPClientPool()
        await pool.initialize({})
        assert pool.clients == {}
        assert pool.tools == {}

    @pytest.mark.asyncio
    async def test_initialize_with_servers(self):
        """Test initialization with server config"""
        config = {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "enabled": True
            }
        }

        pool = MCPClientPool()
        await pool.initialize(config)

        # Verify client was created (mock)
        assert "filesystem" in pool.clients

    @pytest.mark.asyncio
    async def test_connect_stdio_server(self):
        """Test connecting to stdio server"""
        pool = MCPClientPool()
        config = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-test", "/tmp"],
            "enabled": True
        }

        success = await pool._connect_server("test_server", config)
        assert success is True
        assert "test_server" in pool.clients

    @pytest.mark.asyncio
    async def test_get_all_tools(self):
        """Test getting all tools"""
        pool = MCPClientPool()
        config = {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "enabled": True
            }
        }

        await pool.initialize(config)
        tools = pool.get_all_tools()

        assert len(tools) > 0
        assert "filesystem_read_file" in [t["name"] for t in tools]

    @pytest.mark.asyncio
    async def test_get_tools_by_server(self):
        """Test getting tools by server"""
        pool = MCPClientPool()
        config = {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "enabled": True
            }
        }

        await pool.initialize(config)
        tools = pool.get_tools_by_server("filesystem")

        assert len(tools) > 0
        for tool in tools:
            assert tool["server_id"] == "filesystem"

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test calling MCP tool"""
        pool = MCPClientPool()
        config = {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "enabled": True
            }
        }

        await pool.initialize(config)
        result = await pool.call_tool("filesystem_read_file", {"path": "/tmp/test.txt"})

        assert result is not None
        assert "Mock result" in result

    @pytest.mark.asyncio
    async def test_close_pool(self):
        """Test closing pool"""
        pool = MCPClientPool()
        config = {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "enabled": True
            }
        }

        await pool.initialize(config)
        await pool.close()

        assert pool.clients == {}
        assert pool.tools == {}


class TestMCPToolAdapter:
    """Test MCP Tool Adapter"""

    @pytest.mark.asyncio
    async def test_create_adapter(self):
        """Test creating tool adapter"""
        pool = MCPClientPool()
        await pool.initialize({})

        adapter = MCPToolAdapter(pool)
        assert adapter is not None
        assert adapter.mcp_pool == pool

    @pytest.mark.asyncio
    async def test_convert_all_tools(self):
        """Test converting all tools"""
        pool = MCPClientPool()
        config = {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "enabled": True
            }
        }

        await pool.initialize(config)
        adapter = MCPToolAdapter(pool)

        tools = adapter.convert_all_tools()
        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_create_langchain_tool(self):
        """Test creating LangChain tool"""
        pool = MCPClientPool()
        await pool.initialize({})

        adapter = MCPToolAdapter(pool)
        tool_metadata = {
            "name": "test_tool",
            "description": "Test tool",
            "server_id": "test_server"
        }

        tool = adapter.create_langchain_tool(tool_metadata)
        assert tool is not None
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"

    @pytest.mark.asyncio
    async def test_filter_tools_by_names(self):
        """Test filtering tools by names"""
        pool = MCPClientPool()
        config = {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                "enabled": True
            }
        }

        await pool.initialize(config)
        adapter = MCPToolAdapter(pool)

        tools = adapter.filter_tools_by_names(["filesystem_read_file"])
        assert len(tools) > 0
        assert tools[0].name == "filesystem_read_file"


class TestMCPServerManager:
    """Test MCP Server Manager"""

    @pytest.mark.asyncio
    async def test_create_manager(self):
        """Test creating server manager"""
        manager = MCPServerManager()
        assert manager is not None
        assert manager.is_initialized is False

    @pytest.mark.asyncio
    async def test_initialize_with_config(self):
        """Test initialization with config"""
        manager = MCPServerManager()
        config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        await manager.initialize(config)
        assert manager.is_initialized is True

    @pytest.mark.asyncio
    async def test_get_all_tools(self):
        """Test getting all tools"""
        manager = MCPServerManager()
        config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        await manager.initialize(config)
        tools = manager.get_all_tools()

        assert len(tools) > 0

    @pytest.mark.asyncio
    async def test_list_servers(self):
        """Test listing servers"""
        manager = MCPServerManager()
        config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        await manager.initialize(config)
        servers = manager.list_servers()

        assert "filesystem" in servers

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test calling tool through manager"""
        manager = MCPServerManager()
        config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        await manager.initialize(config)
        result = await manager.call_tool("filesystem_read_file", {"path": "/tmp/test.txt"})

        assert result is not None

    @pytest.mark.asyncio
    async def test_close_manager(self):
        """Test closing manager"""
        manager = MCPServerManager()
        config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        await manager.initialize(config)
        await manager.close()

        assert manager.is_initialized is False


class TestGlobalMCPManager:
    """Test global MCP manager singleton"""

    @pytest.mark.asyncio
    async def test_get_global_manager(self):
        """Test getting global manager"""
        reset_mcp_manager()

        config = {
            "servers": {
                "filesystem": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            }
        }

        manager = await get_mcp_manager(config=config)
        assert manager is not None
        assert manager.is_initialized is True

        # Get again - should return same instance
        manager2 = await get_mcp_manager()
        assert manager is manager2

        reset_mcp_manager()

    @pytest.mark.asyncio
    async def test_reset_global_manager(self):
        """Test resetting global manager"""
        reset_mcp_manager()

        manager = await get_mcp_manager(config={"servers": {}})
        assert manager is not None

        reset_mcp_manager()

        # Should create new instance
        manager2 = await get_mcp_manager(config={"servers": {}})
        assert manager is not manager2

        reset_mcp_manager()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])