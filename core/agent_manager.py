"""Agent Loop 管理器"""
from typing import Dict, Optional, List, TYPE_CHECKING
from langchain_core.runnables import Runnable
from skills.registry import SkillRegistry
from core.agent_graph import AgentGraphBuilder
from core.state import AgentState

if TYPE_CHECKING:
    from mcp.server_manager import MCPServerManager


class AgentLoopManager:
    """Agent Loop 管理器"""

    def __init__(
        self,
        llm,
        skill_registry: SkillRegistry,
        mcp_tools: Optional[List] = None,
        checkpointer=None,
        mcp_server_manager: Optional["MCPServerManager"] = None
    ):
        """
        Initialize Agent Loop Manager

        Args:
            llm: Language model instance
            skill_registry: Skill registry instance
            mcp_tools: List of MCP tools (legacy, use mcp_server_manager for new code)
            checkpointer: Checkpoint saver for persistence
            mcp_server_manager: MCP Server Manager instance
        """
        self.llm = llm
        self.skill_registry = skill_registry
        self.checkpointer = checkpointer
        self.agents: Dict[str, Runnable] = {}

        # Support both legacy mcp_tools list and new mcp_server_manager
        # Check if mcp_server_manager is actually a checkpointer (backwards compatibility)
        if mcp_server_manager is not None and hasattr(mcp_server_manager, 'is_initialized'):
            # This is a proper MCPServerManager
            self.mcp_server_manager = mcp_server_manager
            self.mcp_tools = []
        elif mcp_server_manager is not None:
            # This is likely a checkpointer passed in wrong position
            self.mcp_server_manager = None
            self.checkpointer = mcp_server_manager
            self.mcp_tools = mcp_tools or []
        else:
            self.mcp_server_manager = None
            self.mcp_tools = mcp_tools or []

    def get_mcp_tools(self) -> List:
        """
        Get MCP tools from either the server manager or the legacy list

        Returns:
            List of MCP tools
        """
        if self.mcp_server_manager and hasattr(self.mcp_server_manager, 'is_initialized') and self.mcp_server_manager.is_initialized:
            return self.mcp_server_manager.get_all_tools()
        return self.mcp_tools

    def register_agent(self, agent_id: str) -> Runnable:
        """注册并编译一个 Agent"""
        if agent_id in self.agents:
            return self.agents[agent_id]

        # 获取 MCP 工具
        mcp_tools = self.get_mcp_tools()

        # 构建图
        builder = AgentGraphBuilder(self.llm, self.skill_registry, mcp_tools)
        graph = builder.build()

        # 编译图
        compiled = graph.compile(checkpointer=self.checkpointer)
        self.agents[agent_id] = compiled

        return compiled

    def get_agent(self, agent_id: str) -> Optional[Runnable]:
        """获取已编译的 Agent"""
        return self.agents.get(agent_id)

    def reload_agent(self, agent_id: str) -> Runnable:
        """热重载 Agent"""
        # 重新加载 Skills
        if hasattr(self.skill_registry, 'reload_all'):
            self.skill_registry.reload_all()
        elif hasattr(self.skill_registry, 'load_all'):
            self.skill_registry.load_all()

        # 获取 MCP 工具
        mcp_tools = self.get_mcp_tools()

        # 重新编译图
        builder = AgentGraphBuilder(self.llm, self.skill_registry, mcp_tools)
        graph = builder.build()
        compiled = graph.compile(checkpointer=self.checkpointer)

        self.agents[agent_id] = compiled

        return compiled

    async def reload_mcp_server(self, server_id: str) -> bool:
        """
        Reload a specific MCP server

        Args:
            server_id: Server identifier

        Returns:
            True if reload successful
        """
        if self.mcp_server_manager and hasattr(self.mcp_server_manager, 'is_initialized') and self.mcp_server_manager.is_initialized:
            success = await self.mcp_server_manager.reload_server(server_id)
            if success:
                # Rebuild all agents with new tools
                for agent_id in list(self.agents.keys()):
                    self.reload_agent(agent_id)
            return success
        return False

    async def close(self):
        """Close MCP server manager if present"""
        if self.mcp_server_manager and hasattr(self.mcp_server_manager, 'close'):
            await self.mcp_server_manager.close()