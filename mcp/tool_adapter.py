"""MCP Tool Adapter - Converts MCP tools to LangChain Tools"""
from typing import Dict, Any, Optional, List
import logging
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MCPToolAdapter:
    """Adapter for converting MCP tools to LangChain StructuredTools"""

    def __init__(self, mcp_pool: "MCPClientPool"):
        """
        Initialize MCP tool adapter

        Args:
            mcp_pool: MCP client pool instance
        """
        self.mcp_pool = mcp_pool

    def create_langchain_tool(self, tool_metadata: Dict[str, Any]) -> StructuredTool:
        """
        Convert MCP tool metadata to LangChain StructuredTool

        Args:
            tool_metadata: MCP tool metadata from client_pool.get_all_tools()

        Returns:
            LangChain StructuredTool
        """
        tool_name = tool_metadata["name"]
        tool_description = tool_metadata.get("description", f"MCP tool: {tool_name}")
        input_schema = tool_metadata.get("input_schema", {})

        # Create Pydantic model for arguments
        args_model = self._create_args_model(tool_name, input_schema)

        # Create async tool function
        async def tool_func(**kwargs) -> str:
            """Execute MCP tool"""
            try:
                result = await self.mcp_pool.call_tool(tool_name, kwargs)
                return str(result)
            except Exception as e:
                logger.error(f"Error executing MCP tool {tool_name}: {e}")
                return f"Error: {str(e)}"

        # Create StructuredTool
        return StructuredTool(
            name=tool_name,
            description=tool_description,
            args_schema=args_model,
            func=lambda **kwargs: asyncio.run(tool_func(**kwargs)),
            coroutine=tool_func
        )

    def convert_all_tools(self) -> List[StructuredTool]:
        """
        Convert all MCP tools to LangChain Tools

        Returns:
            List of LangChain StructuredTools
        """
        tools_metadata = self.mcp_pool.get_all_tools()
        langchain_tools = []

        for tool_meta in tools_metadata:
            try:
                tool = self.create_langchain_tool(tool_meta)
                langchain_tools.append(tool)
                logger.debug(f"Converted MCP tool to LangChain: {tool_meta['name']}")
            except Exception as e:
                logger.error(f"Failed to convert MCP tool {tool_meta['name']}: {e}")

        logger.info(f"Converted {len(langchain_tools)} MCP tools to LangChain")
        return langchain_tools

    def _create_args_model(self, tool_name: str, input_schema: Dict[str, Any]) -> BaseModel:
        """
        Create Pydantic model from MCP input schema

        Args:
            tool_name: Tool name (used for model class name)
            input_schema: MCP input schema

        Returns:
            Pydantic BaseModel
        """
        fields = {}
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        for field_name, field_def in properties.items():
            field_type = self._convert_type(field_def.get("type", "string"))
            is_required = field_name in required

            # Create field with default
            if is_required:
                field = (field_type, ...)
            else:
                field = (Optional[field_type], None)

            # Add description if available
            if "description" in field_def:
                field_info = Field(description=field_def["description"])
                field = (field_type, Field(default=field_info if not is_required else ...))

            fields[field_name] = field

        # Create dynamic model
        model_name = f"{tool_name.replace('.', '_').replace('-', '_')}_Input"
        return type(model_name, (BaseModel,), {"__annotations__": fields})

    def _convert_type(self, mcp_type: str) -> type:
        """
        Convert MCP type to Python type

        Args:
            mcp_type: MCP type string

        Returns:
            Python type
        """
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": List[Any],
            "object": Dict[str, Any]
        }
        return type_map.get(mcp_type, str)

    def filter_tools_by_names(self, tool_names: List[str]) -> List[StructuredTool]:
        """
        Get LangChain tools by MCP tool names

        Args:
            tool_names: List of MCP tool names

        Returns:
            List of matching LangChain StructuredTools
        """
        all_tools = self.convert_all_tools()
        return [tool for tool in all_tools if tool.name in tool_names]

    def filter_tools_by_server(self, server_id: str) -> List[StructuredTool]:
        """
        Get LangChain tools from a specific MCP server

        Args:
            server_id: MCP server identifier

        Returns:
            List of matching LangChain StructuredTools
        """
        tools_metadata = self.mcp_pool.get_tools_by_server(server_id)
        langchain_tools = []

        for tool_meta in tools_metadata:
            try:
                tool = self.create_langchain_tool(tool_meta)
                langchain_tools.append(tool)
            except Exception as e:
                logger.error(f"Failed to convert MCP tool {tool_meta['name']}: {e}")

        return langchain_tools


# Import asyncio at module level
import asyncio