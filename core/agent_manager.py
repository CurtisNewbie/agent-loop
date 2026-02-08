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
        mcp_server_manager: Optional["MCPServerManager"] = None,
        enable_memory_compaction: bool = False,
        memory_compaction_strategy: str = "token_aware",
        memory_compaction_max_tokens: Optional[int] = None,
        memory_compaction_max_messages: Optional[int] = None,
    ):
        """
        Initialize Agent Loop Manager

        Args:
            llm: Language model instance
            skill_registry: Skill registry instance
            mcp_tools: List of MCP tools (legacy, use mcp_server_manager for new code)
            checkpointer: Checkpoint saver for persistence
            mcp_server_manager: MCP Server Manager instance
            enable_memory_compaction: Whether to enable memory compaction globally
            memory_compaction_strategy: Default compaction strategy ("sliding_window", "token_aware", "summary", "hybrid")
            memory_compaction_max_tokens: Maximum tokens to keep per conversation
            memory_compaction_max_messages: Maximum messages to keep (for sliding window)
        """
        self.llm = llm
        self.skill_registry = skill_registry
        self.checkpointer = checkpointer
        self.agents: Dict[str, Runnable] = {}
        self.agent_configs: Dict[str, Dict[str, any]] = {}  # Store agent configurations

        # Memory compaction settings
        self.enable_memory_compaction = enable_memory_compaction
        self.memory_compaction_strategy = memory_compaction_strategy
        self.memory_compaction_max_tokens = memory_compaction_max_tokens
        self.memory_compaction_max_messages = memory_compaction_max_messages

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

    def register_agent(
        self,
        agent_id: str,
        allowed_skills: Optional[List[str]] = None,
        enable_memory_compaction: Optional[bool] = None,
        memory_compaction_strategy: Optional[str] = None,
        memory_compaction_max_tokens: Optional[int] = None,
        memory_compaction_max_messages: Optional[int] = None,
    ) -> Runnable:
        """
        注册并编译一个 Agent

        Args:
            agent_id: Agent 唯一标识符
            allowed_skills: 允许该 Agent 使用的 Skill ID 列表。如果为 None，则使用所有 Skills
            enable_memory_compaction: Whether to enable memory compaction for this agent (overrides global setting)
            memory_compaction_strategy: Compaction strategy (overrides global setting)
            memory_compaction_max_tokens: Maximum tokens (overrides global setting)
            memory_compaction_max_messages: Maximum messages (overrides global setting)

        Returns:
            Compiled LangGraph Runnable
        """
        if agent_id in self.agents:
            return self.agents[agent_id]

        # 保存 Agent 配置
        self.agent_configs[agent_id] = {
            "allowed_skills": allowed_skills,
            "enable_memory_compaction": enable_memory_compaction,
            "memory_compaction_strategy": memory_compaction_strategy,
            "memory_compaction_max_tokens": memory_compaction_max_tokens,
            "memory_compaction_max_messages": memory_compaction_max_messages,
        }

        # 构建并编译
        compiled = self._build_and_compile(
            allowed_skills,
            enable_memory_compaction,
            memory_compaction_strategy,
            memory_compaction_max_tokens,
            memory_compaction_max_messages,
        )
        self.agents[agent_id] = compiled

        return compiled

    def _build_and_compile(
        self,
        allowed_skills: Optional[List[str]] = None,
        enable_memory_compaction: Optional[bool] = None,
        memory_compaction_strategy: Optional[str] = None,
        memory_compaction_max_tokens: Optional[int] = None,
        memory_compaction_max_messages: Optional[int] = None,
    ) -> Runnable:
        """
        内部方法：构建并编译 Agent Graph

        Args:
            allowed_skills: 允许的 Skill ID 列表
            enable_memory_compaction: Whether to enable memory compaction
            memory_compaction_strategy: Compaction strategy
            memory_compaction_max_tokens: Maximum tokens
            memory_compaction_max_messages: Maximum messages

        Returns:
            Compiled LangGraph Runnable
        """
        # 获取 MCP 工具
        mcp_tools = self.get_mcp_tools()

        # 根据 allowed_skills 过滤 Skill 工具
        if allowed_skills:
            skill_tools = self.skill_registry.get_tools_by_skill_ids(allowed_skills)
        else:
            skill_tools = self.skill_registry.get_all_langchain_tools()

        # Resolve memory compaction settings (agent-level overrides global)
        enable_compaction = enable_memory_compaction if enable_memory_compaction is not None else self.enable_memory_compaction
        strategy = memory_compaction_strategy or self.memory_compaction_strategy
        max_tokens = memory_compaction_max_tokens if memory_compaction_max_tokens is not None else self.memory_compaction_max_tokens
        max_messages = memory_compaction_max_messages if memory_compaction_max_messages is not None else self.memory_compaction_max_messages

        # Create memory compactor if enabled
        memory_compactor = None
        if enable_compaction:
            from core.memory_compactor import create_memory_compactor
            memory_compactor = create_memory_compactor(
                llm=self.llm,
                strategy=strategy,
                max_tokens=max_tokens,
                max_messages=max_messages,
            )

        # 构建图（传入过滤后的 Skill 工具和 memory compactor）
        builder = AgentGraphBuilder(
            self.llm,
            self.skill_registry,
            mcp_tools,
            skill_tools,
            enable_memory_compaction=enable_compaction,
            memory_compactor=memory_compactor,
        )
        graph = builder.build()

        # 编译图
        compiled = graph.compile(checkpointer=self.checkpointer)

        return compiled

    def get_agent(self, agent_id: str) -> Optional[Runnable]:
        """获取已编译的 Agent"""
        return self.agents.get(agent_id)

    def reload_agent(self, agent_id: str) -> Runnable:
        """
        热重载 Agent（保留配置）
        """
        if agent_id not in self.agent_configs:
            raise ValueError(f"Agent {agent_id} not found")

        # 重新加载 Skills
        if hasattr(self.skill_registry, 'reload_all'):
            self.skill_registry.reload_all()
        elif hasattr(self.skill_registry, 'load_all'):
            self.skill_registry.load_all()

        # 获取保存的配置
        config = self.agent_configs[agent_id]

        # 使用 _build_and_compile 重新构建
        compiled = self._build_and_compile(
            allowed_skills=config.get("allowed_skills"),
            enable_memory_compaction=config.get("enable_memory_compaction"),
            memory_compaction_strategy=config.get("memory_compaction_strategy"),
            memory_compaction_max_tokens=config.get("memory_compaction_max_tokens"),
            memory_compaction_max_messages=config.get("memory_compaction_max_messages"),
        )
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