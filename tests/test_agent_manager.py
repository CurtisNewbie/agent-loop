"""Agent Loop Manager 测试"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from core.agent_manager import AgentLoopManager
from skills.registry import SkillRegistry


class TestAgentLoopManager:
    """测试 Agent Loop Manager"""

    def test_register_agent_with_allowed_skills(self):
        """测试注册 Agent 时指定 allowed_skills"""
        # 创建 mock LLM
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # 创建 mock MCP tools
        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "read_file"

        # 创建 Skill Registry（初始化时不加载，避免 mock LLM 问题）
        skill_registry = SkillRegistry.__new__(SkillRegistry)
        skill_registry.llm = mock_llm
        skill_registry.mcp_tools = [mock_mcp_tool]
        skill_registry.skills_dir = "skills"
        skill_registry.skills = {}
        skill_registry.langchain_tools = {}

        # 手动添加一个 mock skill tool
        mock_skill_tool = Mock()
        mock_skill_tool.name = "code_review"
        skill_registry.skills["code_review"] = Mock(id="code_review")
        skill_registry.langchain_tools["code_review"] = mock_skill_tool

        # 创建 Agent Manager
        manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=skill_registry,
            mcp_tools=[mock_mcp_tool],
            checkpointer=None
        )

        # Mock the build process to avoid actual graph construction
        with patch.object(manager, '_build_and_compile') as mock_build:
            mock_build.return_value = Mock()

            # 注册 Agent，只允许使用 code_review Skill
            agent = manager.register_agent(
                agent_id="code_reviewer",
                allowed_skills=["code_review"]
            )

            # 验证 Agent 已注册
            assert agent is not None
            assert "code_reviewer" in manager.agents

            # 验证配置已保存
            assert "code_reviewer" in manager.agent_configs
            assert manager.agent_configs["code_reviewer"]["allowed_skills"] == ["code_review"]

    def test_register_agent_without_allowed_skills(self):
        """测试注册 Agent 时不指定 allowed_skills（使用所有 Skills）"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "read_file"

        # 创建 Skill Registry（不自动加载）
        skill_registry = SkillRegistry.__new__(SkillRegistry)
        skill_registry.llm = mock_llm
        skill_registry.mcp_tools = [mock_mcp_tool]
        skill_registry.skills_dir = "skills"
        skill_registry.skills = {}
        skill_registry.langchain_tools = {}

        # 手动添加 mock skill tools
        mock_skill_tool1 = Mock()
        mock_skill_tool1.name = "code_review"
        mock_skill_tool2 = Mock()
        mock_skill_tool2.name = "data_analysis"
        skill_registry.skills["code_review"] = Mock(id="code_review")
        skill_registry.skills["data_analysis"] = Mock(id="data_analysis")
        skill_registry.langchain_tools["code_review"] = mock_skill_tool1
        skill_registry.langchain_tools["data_analysis"] = mock_skill_tool2

        manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=skill_registry,
            mcp_tools=[mock_mcp_tool],
            checkpointer=None
        )

        # Mock the build process
        with patch.object(manager, '_build_and_compile') as mock_build:
            mock_build.return_value = Mock()

            # 注册 Agent，不指定 allowed_skills
            agent = manager.register_agent(agent_id="general_agent")

            # 验证 Agent 已注册
            assert agent is not None
            assert "general_agent" in manager.agents

            # 验证配置中 allowed_skills 为 None
            assert manager.agent_configs["general_agent"]["allowed_skills"] is None

    def test_get_tools_by_skill_ids(self):
        """测试 SkillRegistry 的 get_tools_by_skill_ids 方法"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # 创建 Skill Registry（不自动加载）
        skill_registry = SkillRegistry.__new__(SkillRegistry)
        skill_registry.llm = mock_llm
        skill_registry.mcp_tools = []
        skill_registry.skills_dir = "skills"
        skill_registry.skills = {}
        skill_registry.langchain_tools = {}

        # 手动添加 mock skill tool
        mock_skill_tool = Mock()
        mock_skill_tool.name = "code_review"
        skill_registry.skills["code_review"] = Mock(id="code_review")
        skill_registry.langchain_tools["code_review"] = mock_skill_tool

        # 获取指定 Skill 的 Tools
        tools = skill_registry.get_tools_by_skill_ids(["code_review"])

        # 验证返回正确的 Tool
        assert len(tools) == 1
        assert tools[0].name == "code_review"

        # 测试获取多个 Skills 的 Tools
        all_tools = skill_registry.get_all_langchain_tools()
        all_skill_ids = [tool.name for tool in all_tools]
        filtered_tools = skill_registry.get_tools_by_skill_ids(all_skill_ids)

        assert len(filtered_tools) == len(all_tools)

    def test_get_tools_by_skill_ids_invalid_skill(self):
        """测试使用无效的 Skill ID"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # 创建 Skill Registry（不自动加载）
        skill_registry = SkillRegistry.__new__(SkillRegistry)
        skill_registry.llm = mock_llm
        skill_registry.mcp_tools = []
        skill_registry.skills_dir = "skills"
        skill_registry.skills = {}
        skill_registry.langchain_tools = {}

        # 手动添加 mock skill tool
        mock_skill_tool = Mock()
        mock_skill_tool.name = "code_review"
        skill_registry.skills["code_review"] = Mock(id="code_review")
        skill_registry.langchain_tools["code_review"] = mock_skill_tool

        # 使用不存在的 Skill ID
        tools = skill_registry.get_tools_by_skill_ids(["nonexistent_skill"])

        # 验证返回空列表
        assert len(tools) == 0

        # 混合有效和无效的 Skill ID
        tools = skill_registry.get_tools_by_skill_ids(["code_review", "nonexistent_skill"])

        # 验证只返回有效的 Tool
        assert len(tools) == 1
        assert tools[0].name == "code_review"

    def test_reload_agent_preserves_allowed_skills(self):
        """测试 reload_agent 保留 allowed_skills 配置"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "read_file"

        # 创建 Skill Registry（不自动加载）
        skill_registry = SkillRegistry.__new__(SkillRegistry)
        skill_registry.llm = mock_llm
        skill_registry.mcp_tools = [mock_mcp_tool]
        skill_registry.skills_dir = "skills"
        skill_registry.skills = {}
        skill_registry.langchain_tools = {}

        # 手动添加 mock skill tool
        mock_skill_tool = Mock()
        mock_skill_tool.name = "code_review"
        skill_registry.skills["code_review"] = Mock(id="code_review")
        skill_registry.langchain_tools["code_review"] = mock_skill_tool

        manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=skill_registry,
            mcp_tools=[mock_mcp_tool],
            checkpointer=None
        )

        # Mock the build process and load_all
        with patch.object(manager, '_build_and_compile') as mock_build, \
             patch.object(skill_registry, 'load_all') as mock_load:
            mock_build.return_value = Mock()

            # 注册 Agent 并指定 allowed_skills
            manager.register_agent(
                agent_id="test_agent",
                allowed_skills=["code_review"]
            )

            # 重载 Agent
            reloaded_agent = manager.reload_agent("test_agent")

            # 验证 Agent 已重载
            assert reloaded_agent is not None

            # 验证 allowed_skills 配置已保留
            assert manager.agent_configs["test_agent"]["allowed_skills"] == ["code_review"]

    def test_reload_nonexistent_agent(self):
        """测试重载不存在的 Agent"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "read_file"

        # 创建 Skill Registry（不自动加载）
        skill_registry = SkillRegistry.__new__(SkillRegistry)
        skill_registry.llm = mock_llm
        skill_registry.mcp_tools = [mock_mcp_tool]
        skill_registry.skills_dir = "skills"
        skill_registry.skills = {}
        skill_registry.langchain_tools = {}

        manager = AgentLoopManager(
            llm=mock_llm,
            skill_registry=skill_registry,
            mcp_tools=[mock_mcp_tool],
            checkpointer=None
        )

        # 尝试重载不存在的 Agent
        with pytest.raises(ValueError, match="Agent nonexistent_agent not found"):
            manager.reload_agent("nonexistent_agent")

    def test_get_skills_by_ids(self):
        """测试 get_skills_by_ids 方法"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # 创建 Skill Registry（不自动加载）
        skill_registry = SkillRegistry.__new__(SkillRegistry)
        skill_registry.llm = mock_llm
        skill_registry.mcp_tools = []
        skill_registry.skills_dir = "skills"
        skill_registry.skills = {}
        skill_registry.langchain_tools = {}

        # 手动添加 mock skill
        mock_skill = Mock()
        mock_skill.id = "code_review"
        skill_registry.skills["code_review"] = mock_skill

        # 获取指定 Skill ID 的 Skill 对象
        skills = skill_registry.get_skills_by_ids(["code_review"])

        # 验证返回正确的 Skill
        assert len(skills) == 1
        assert skills[0].id == "code_review"

        # 混合有效和无效的 Skill ID
        skills = skill_registry.get_skills_by_ids(["code_review", "nonexistent"])

        # 验证只返回有效的 Skill
        assert len(skills) == 1
        assert skills[0].id == "code_review"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])