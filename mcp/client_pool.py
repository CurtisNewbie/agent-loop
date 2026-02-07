"""MCP Client Pool - Manages connections to MCP servers"""
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MCPClientPool:
    """Pool of MCP client connections"""

    def __init__(self):
        self.clients: Dict[str, Any] = {}  # server_id -> client session
        self.tools: Dict[str, Any] = {}  # tool_name -> tool
        self.server_configs: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

    async def initialize(self, servers_config: Dict[str, Dict]):
        """
        Initialize MCP client pool with server configurations

        Args:
            servers_config: Dict mapping server_id to config
                {
                    "filesystem": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
                        "enabled": True
                    }
                }
        """
        self.server_configs = servers_config

        # Connect to all enabled servers
        tasks = []
        for server_id, config in servers_config.items():
            if config.get("enabled", False):
                tasks.append(self._connect_server(server_id, config))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"MCP initialized: {success_count}/{len(tasks)} servers connected")

    async def _connect_server(self, server_id: str, config: Dict) -> bool:
        """
        Connect to a single MCP server

        Args:
            server_id: Unique server identifier
            config: Server configuration

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if config["type"] == "stdio":
                client = await self._connect_stdio_server(server_id, config)
            else:
                logger.error(f"Unsupported MCP server type: {config['type']}")
                return False

            if client:
                self.clients[server_id] = client
                await self._discover_tools(server_id, client)
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to connect MCP server {server_id}: {e}")
            return False

    async def _connect_stdio_server(self, server_id: str, config: Dict) -> Optional[Any]:
        """
        Connect to MCP server via stdio

        Args:
            server_id: Server identifier
            config: Server configuration

        Returns:
            Client session or None
        """
        # For now, create a mock client since we don't have the MCP SDK
        # In production, this would use the actual MCP SDK
        logger.info(f"Connecting to stdio MCP server: {server_id}")

        # Mock client for development
        class MockClient:
            def __init__(self, server_id: str):
                self.server_id = server_id

            async def initialize(self):
                logger.info(f"Mock client {self.server_id} initialized")

            async def list_tools(self):
                # Return mock tools with proper structure
                class ListToolsResponse:
                    def __init__(self, tools):
                        self.tools = tools

                tools = [
                    {
                        "name": f"{self.server_id}_read_file",
                        "description": f"Read file from {self.server_id}",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "File path"}
                            },
                            "required": ["path"]
                        }
                    },
                    {
                        "name": f"{self.server_id}_write_file",
                        "description": f"Write file to {self.server_id}",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string", "description": "File path"},
                                "content": {"type": "string", "description": "File content"}
                            },
                            "required": ["path", "content"]
                        }
                    }
                ]
                return ListToolsResponse(tools)

            async def call_tool(self, name: str, arguments: Dict) -> Any:
                logger.info(f"Mock call_tool: {name} with {arguments}")
                return f"Mock result from {name}"

            async def close(self):
                logger.info(f"Mock client {self.server_id} closed")

        client = MockClient(server_id)
        await client.initialize()
        return client

    async def _discover_tools(self, server_id: str, client: Any):
        """
        Discover and register tools from MCP server

        Args:
            server_id: Server identifier
            client: Client session
        """
        try:
            response = await client.list_tools()

            if hasattr(response, 'tools'):
                tools_list = response.tools
            elif isinstance(response, dict) and 'tools' in response:
                tools_list = response['tools']
            else:
                logger.warning(f"Unexpected tool list format from {server_id}")
                return

            for tool in tools_list:
                tool_name = tool.get("name")
                if tool_name:
                    self.tools[tool_name] = {
                        "server_id": server_id,
                        "description": tool.get("description", ""),
                        "input_schema": tool.get("inputSchema", {}),
                        "client": client
                    }
                    logger.debug(f"Registered MCP tool: {tool_name} from {server_id}")

        except Exception as e:
            logger.error(f"Failed to discover tools from {server_id}: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result
        """
        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        client = tool["client"]
        try:
            result = await client.call_tool(tool_name, arguments)

            # Extract content from result
            if hasattr(result, 'content'):
                content = result.content
                if isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    if hasattr(first_item, 'text'):
                        return first_item.text
                    return str(first_item)
                return str(content)
            return str(result)

        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Get all available MCP tools

        Returns:
            List of tool metadata
        """
        return [
            {
                "name": name,
                "description": tool["description"],
                "server_id": tool["server_id"]
            }
            for name, tool in self.tools.items()
        ]

    def get_tools_by_server(self, server_id: str) -> List[Dict[str, Any]]:
        """
        Get tools from a specific server

        Args:
            server_id: Server identifier

        Returns:
            List of tool metadata
        """
        return [
            {
                "name": name,
                "description": tool["description"],
                "server_id": tool["server_id"]
            }
            for name, tool in self.tools.items()
            if tool["server_id"] == server_id
        ]

    async def close(self):
        """Close all MCP client connections"""
        tasks = []
        for server_id, client in self.clients.items():
            if hasattr(client, 'close'):
                tasks.append(client.close())

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self.clients.clear()
        self.tools.clear()
        logger.info("MCP client pool closed")

    @classmethod
    def from_config_file(cls, config_path: str) -> "MCPClientPool":
        """
        Create MCP client pool from configuration file

        Args:
            config_path: Path to YAML configuration file

        Returns:
            MCPClientPool instance (not initialized yet)
        """
        import yaml

        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"MCP config not found: {config_path}")

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        pool = cls()
        pool.server_configs = config.get('servers', {})
        return pool