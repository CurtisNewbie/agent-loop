"""MCP Server Manager - Manages MCP server lifecycle"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from mcp.client_pool import MCPClientPool
from mcp.tool_adapter import MCPToolAdapter

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages MCP server connections and provides unified tool interface"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize MCP Server Manager

        Args:
            config_path: Path to MCP server configuration file (YAML)
        """
        self.config_path = config_path
        self.client_pool: Optional[MCPClientPool] = None
        self.tool_adapter: Optional[MCPToolAdapter] = None
        self._initialized = False

    async def initialize(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize MCP servers

        Args:
            config: Server configuration dict (overrides config file if provided)
        """
        if self._initialized:
            logger.warning("MCP Server Manager already initialized")
            return

        # Load configuration
        if config:
            servers_config = config.get("servers", {})
        elif self.config_path:
            self.client_pool = MCPClientPool.from_config_file(self.config_path)
            servers_config = self.client_pool.server_configs
        else:
            servers_config = {}

        # Create client pool if not already created
        if not self.client_pool:
            self.client_pool = MCPClientPool()

        # Initialize client pool
        if servers_config:
            await self.client_pool.initialize(servers_config)

        # Create tool adapter
        self.tool_adapter = MCPToolAdapter(self.client_pool)

        self._initialized = True
        logger.info("MCP Server Manager initialized")

    def get_all_tools(self) -> List[Any]:
        """
        Get all MCP tools as LangChain Tools

        Returns:
            List of LangChain StructuredTools
        """
        if not self._initialized:
            logger.warning("MCP Server Manager not initialized")
            return []

        return self.tool_adapter.convert_all_tools()

    def get_tools_by_server(self, server_id: str) -> List[Any]:
        """
        Get tools from a specific MCP server

        Args:
            server_id: Server identifier

        Returns:
            List of LangChain StructuredTools
        """
        if not self._initialized:
            logger.warning("MCP Server Manager not initialized")
            return []

        return self.tool_adapter.filter_tools_by_server(server_id)

    def get_tools_by_names(self, tool_names: List[str]) -> List[Any]:
        """
        Get specific MCP tools by name

        Args:
            tool_names: List of tool names

        Returns:
            List of LangChain StructuredTools
        """
        if not self._initialized:
            logger.warning("MCP Server Manager not initialized")
            return []

        return self.tool_adapter.filter_tools_by_names(tool_names)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool directly

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool result
        """
        if not self._initialized:
            raise RuntimeError("MCP Server Manager not initialized")

        return await self.client_pool.call_tool(tool_name, arguments)

    def list_servers(self) -> List[str]:
        """
        List all connected MCP servers

        Returns:
            List of server IDs
        """
        if not self._initialized:
            return []

        return list(self.client_pool.clients.keys())

    def list_tools_metadata(self) -> List[Dict[str, Any]]:
        """
        List metadata for all MCP tools

        Returns:
            List of tool metadata
        """
        if not self._initialized:
            return []

        return self.client_pool.get_all_tools()

    async def reload_server(self, server_id: str) -> bool:
        """
        Reload a specific MCP server

        Args:
            server_id: Server identifier

        Returns:
            True if reload successful
        """
        if not self._initialized:
            logger.warning("MCP Server Manager not initialized")
            return False

        # Close existing connection
        if server_id in self.client_pool.clients:
            client = self.client_pool.clients[server_id]
            if hasattr(client, 'close'):
                await client.close()
            del self.client_pool.clients[server_id]

        # Remove tools from this server
        self.client_pool.tools = {
            name: tool
            for name, tool in self.client_pool.tools.items()
            if tool["server_id"] != server_id
        }

        # Reconnect
        config = self.client_pool.server_configs.get(server_id)
        if config and config.get("enabled", False):
            success = await self.client_pool._connect_server(server_id, config)
            if success:
                logger.info(f"Reloaded MCP server: {server_id}")
            return success

        return False

    async def close(self):
        """Close all MCP server connections"""
        if self.client_pool:
            await self.client_pool.close()
        self._initialized = False
        logger.info("MCP Server Manager closed")

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized"""
        return self._initialized


# Singleton instance for global access
_manager_instance: Optional[MCPServerManager] = None


async def get_mcp_manager(config_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> MCPServerManager:
    """
    Get or create global MCP Server Manager instance

    Args:
        config_path: Path to MCP configuration file
        config: Server configuration dict (overrides config file if provided)

    Returns:
        MCPServerManager instance
    """
    global _manager_instance

    if _manager_instance is None:
        _manager_instance = MCPServerManager(config_path=config_path)
        await _manager_instance.initialize(config=config)

    return _manager_instance


def reset_mcp_manager():
    """Reset global MCP Server Manager instance (for testing)"""
    global _manager_instance
    _manager_instance = None