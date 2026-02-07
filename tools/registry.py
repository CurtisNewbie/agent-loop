"""Tools Registry - Central registry for all available tools."""
from typing import List, Dict, Optional
from langchain_core.tools import BaseTool

from tools.shell_tool import shell_tool
from tools.http_tool import http_tool
from tools.file_tool import (
    read_file_tool,
    write_file_tool,
    list_directory_tool,
    delete_file_tool
)


class ToolRegistry:
    """Registry for managing all available tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools."""
        self.register(shell_tool)
        self.register(http_tool)
        self.register(read_file_tool)
        self.register(write_file_tool)
        self.register(list_directory_tool)
        self.register(delete_file_tool)
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool.
        
        Args:
            tool: Tool to register
        """
        self._tools[tool.name] = tool
    
    def unregister(self, tool_name: str) -> None:
        """Unregister a tool.
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name.
        
        Args:
            tool_name: Name of tool to get
            
        Returns:
            Tool or None if not found
        """
        return self._tools.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_all(self) -> List[BaseTool]:
        """Get all registered tools.
        
        Returns:
            List of all tools
        """
        return list(self._tools.values())
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
    
    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tools


# Global registry instance
tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry.
    
    Returns:
        Global ToolRegistry instance
    """
    return tool_registry


def get_all_tools() -> List[BaseTool]:
    """Get all tools from the global registry.
    
    Returns:
        List of all tools
    """
    return tool_registry.get_all()


__all__ = [
    "ToolRegistry",
    "tool_registry",
    "get_tool_registry",
    "get_all_tools"
]
