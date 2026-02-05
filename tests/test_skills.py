"""Skill 系统测试"""
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from skills.schemas import Skill, SkillFrontmatter
from skills.loader import SkillLoader
from skills.converter import skill_to_langchain_tool
from skills.registry import SkillRegistry


class TestSkillLoader:
    """测试 Skill Loader"""

    def test_load_code_review_skill(self):
        """测试加载 code_review Skill"""
        skill: Skill = SkillLoader.load("skills/code_review")

        # 验证 Frontmatter
        assert skill.frontmatter.name == "code_review"
        assert skill.frontmatter.version == "1.0.0"
        assert "comprehensive code review" in skill.frontmatter.description.lower()

        # 验证工具列表
        allowed_tools = skill.frontmatter.get_allowed_tools()
        assert "read_file" in allowed_tools
        assert "write_file" in allowed_tools

        # 验证内容
        assert len(skill.content) > 0
        assert "Code Review Skill" in skill.content
        assert "Step 1: Understand the Code" in skill.content

    def test_load_skill_with_scripts(self):
        """测试加载带脚本的 Skill"""
        skill: Skill = SkillLoader.load("skills/code_review")

        # uv run pytest tests/test_skills.py::TestSkillLoader::test_load_skill_with_scripts -v -s
        print(f"\n{'='*60}")
        print(f"Skill ID: {skill.id}")
        print(f"Skill Full ID: {skill.full_id}")
        print(f"Skill Path: {skill.skill_path}")
        print(f"\nFrontmatter:")
        print(f"  Name: {skill.frontmatter.name}")
        print(f"  Description: {skill.frontmatter.description}")
        print(f"  Version: {skill.frontmatter.version}")
        print(f"  License: {skill.frontmatter.license}")
        print(f"  Allowed Tools: {skill.frontmatter.get_allowed_tools()}")
        print(f"\nContent Length: {len(skill.content)} chars")
        print(f"Content Preview: {skill.content[:100]}...")
        print(f"\nScripts: {skill.scripts}")
        print(f"References: {skill.references}")
        print(f"Assets: {skill.assets}")
        print(f"\nScript Tools: {len(skill.script_tools)} tools")
        for i, tool in enumerate(skill.script_tools):
            print(f"  [{i}] {tool.name}: {tool.description[:60]}...")
            print(f"      Args: {list(tool.args_schema.model_fields.keys())}")
        print(f"{'='*60}\n")

        # 验证脚本工具已加载
        assert len(skill.script_tools) > 0

        # 验证脚本工具名称
        tool_names = [tool.name for tool in skill.script_tools]
        assert "code_review_linter" in tool_names
        assert "code_review_security_check" in tool_names

    def test_load_nonexistent_skill(self):
        """测试加载不存在的 Skill"""
        with pytest.raises(FileNotFoundError):
            SkillLoader.load("skills/nonexistent")

    def test_parse_frontmatter(self):
        """测试 Frontmatter 解析"""
        skill = SkillLoader.load("skills/code_review")

        # 验证所有必需字段
        assert skill.frontmatter.name
        assert skill.frontmatter.description
        assert skill.frontmatter.version
        assert skill.frontmatter.license


class TestScriptLoader:
    """测试脚本加载功能"""

    def test_load_tool_decorator_script(self):
        """测试加载使用 @tool 装饰器的脚本"""
        skill: Skill = SkillLoader.load("skills/code_review")

        # 查找 code_review_linter 工具
        linter_tool = next((t for t in skill.script_tools if t.name == "code_review_linter"), None)

        assert linter_tool is not None
        assert linter_tool.name == "code_review_linter"
        assert "linting" in linter_tool.description.lower()

    def test_load_named_function_script(self):
        """测试加载使用规范命名的函数脚本"""
        skill: Skill = SkillLoader.load("skills/code_review")

        # 查找 code_review_security_check 工具
        security_tool = next((t for t in skill.script_tools if t.name == "code_review_security_check"), None)

        assert security_tool is not None
        assert security_tool.name == "code_review_security_check"
        assert "security" in security_tool.description.lower()

    def test_script_tool_execution(self):
        """测试脚本工具执行"""
        skill: Skill = SkillLoader.load("skills/code_review")

        # 创建测试文件
        test_file = Path("/tmp/test_script_file.py")
        test_file.write_text('def test():\n    pass\n', encoding="utf-8")

        try:
            # 获取 linter 工具
            linter_tool = next((t for t in skill.script_tools if t.name == "code_review_linter"), None)

            # 执行工具
            result = linter_tool.func(str(test_file))

            # 验证结果
            assert result is not None
            assert "Linting Issues" in result or "No linting issues" in result
        finally:
            # 清理测试文件
            if test_file.exists():
                test_file.unlink()

    def test_skill_all_tools_property(self):
        """测试 all_tools 属性"""
        skill: Skill = SkillLoader.load("skills/code_review")

        # 验证 all_tools 返回脚本工具
        all_tools = skill.all_tools
        assert len(all_tools) == len(skill.script_tools)

        # 验证工具类型
        from langchain_core.tools import BaseTool
        assert all(isinstance(tool, BaseTool) for tool in all_tools)


class TestSkillConverter:
    """测试 Skill Converter"""

    @pytest.mark.asyncio
    async def test_skill_to_langchain_tool(self):
        """测试 SKILL.md → LangChain Tool 转换"""
        # 加载 Skill
        skill = SkillLoader.load("skills/code_review")

        # 创建 mock LLM 和 MCP tools
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        mock_tool = Mock()
        mock_tool.name = "read_file"
        mock_tool.ainvoke = AsyncMock(return_value="file content")

        mcp_tools = [mock_tool]

        # 转换为 LangChain Tool
        langchain_tool = skill_to_langchain_tool(skill, mock_llm, mcp_tools)

        # 验证 Tool 属性
        assert langchain_tool.name == "code_review"
        assert "comprehensive code review" in langchain_tool.description.lower()
        assert langchain_tool.args_schema is not None

    @pytest.mark.asyncio
    async def test_skill_tool_filters_allowed_tools(self):
        """测试 Skill 只使用允许的工具（包括脚本工具）"""
        skill = SkillLoader.load("skills/code_review")

        # 创建 mock LLM
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=Mock(tool_calls=[], content="result"))

        # 创建多个 MCP tools
        mock_read_tool = Mock(name="read_file")
        mock_read_tool.name = "read_file"
        mock_read_tool.ainvoke = AsyncMock(return_value="file content")

        mock_write_tool = Mock(name="write_file")
        mock_write_tool.name = "write_file"
        mock_write_tool.ainvoke = AsyncMock(return_value="written")

        mock_other_tool = Mock(name="other_tool")
        mock_other_tool.name = "other_tool"

        mcp_tools = [mock_read_tool, mock_write_tool, mock_other_tool]

        # 转换 Skill
        langchain_tool = skill_to_langchain_tool(skill, mock_llm, mcp_tools)

        # 验证：Tool 创建成功
        assert langchain_tool.name == "code_review"

        # 执行 Tool 以触发过滤逻辑
        await langchain_tool.ainvoke({"user_input": "test"})

        # 验证：bind_tools 被调用且只包含允许的工具
        mock_llm.bind_tools.assert_called()
        call_args = mock_llm.bind_tools.call_args[0][0]

        # 只应该包含 read_file 和 write_file
        allowed_tool_names = [t.name for t in call_args]
        assert "read_file" in allowed_tool_names
        assert "write_file" in allowed_tool_names
        assert "other_tool" not in allowed_tool_names

    @pytest.mark.asyncio
    async def test_skill_includes_script_tools(self):
        """测试 Skill 转换包含脚本工具"""
        skill = SkillLoader.load("skills/code_review")

        # 验证脚本工具已加载
        assert len(skill.script_tools) > 0

        # 创建 mock LLM
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=Mock(tool_calls=[], content="result"))

        # 转换 Skill
        langchain_tool = skill_to_langchain_tool(skill, mock_llm, [])

        # 执行 Tool
        await langchain_tool.ainvoke({"user_input": "test"})

        # 验证：脚本工具被包含在绑定中
        mock_llm.bind_tools.assert_called()
        call_args = mock_llm.bind_tools.call_args[0][0]

        # 验证脚本工具在列表中
        tool_names = [t.name for t in call_args]
        assert "code_review_linter" in tool_names
        assert "code_review_security_check" in tool_names


class TestSkillRegistry:
    """测试 Skill Registry"""

    def test_registry_initialization(self):
        """测试 Registry 初始化"""
        # 创建 mock LLM
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        # 创建 Registry
        registry = SkillRegistry(mock_llm, [], "skills")

        # 验证自动加载
        assert len(registry.skills) > 0
        assert "code_review" in registry.skills

    def test_get_skill(self):
        """测试获取 Skill"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        registry = SkillRegistry(mock_llm, [], "skills")

        skill = registry.get_skill("code_review")
        assert skill is not None
        assert skill.frontmatter.name == "code_review"

    def test_get_langchain_tools(self):
        """测试获取所有 LangChain Tools"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        registry = SkillRegistry(mock_llm, [], "skills")

        tools = registry.get_all_langchain_tools()
        assert len(tools) > 0

        # 验证 code_review tool
        code_review_tool = next((t for t in tools if t.name == "code_review"), None)
        assert code_review_tool is not None

    def test_list_skills(self):
        """测试列出所有 Skills"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        registry = SkillRegistry(mock_llm, [], "skills")

        skills = registry.list_skills()
        assert len(skills) > 0

        # 验证 code_review skill
        code_review_skill = next((s for s in skills if s.id == "code_review"), None)
        assert code_review_skill is not None

    def test_reload_skill(self):
        """测试重载 Skill"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        registry = SkillRegistry(mock_llm, [], "skills")

        # 重载 code_review
        registry.reload("code_review")

        # 验证 Skill 仍然存在
        assert "code_review" in registry.skills

    def test_reload_nonexistent_skill(self):
        """测试重载不存在的 Skill"""
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        registry = SkillRegistry(mock_llm, [], "skills")

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="Skill not found"):
            registry.reload("nonexistent")


class TestSkillIntegration:
    """Skill 系统集成测试"""

    def test_full_skill_workflow(self):
        """测试完整的 Skill 工作流"""
        # 1. 加载 Skill
        skill = SkillLoader.load("skills/code_review")
        assert skill is not None

        # 2. 验证 Skill 数据
        assert skill.frontmatter.name == "code_review"
        assert skill.frontmatter.version == "1.0.0"
        assert len(skill.content) > 0

        # 3. 创建 Registry
        mock_llm = Mock()
        mock_llm.bind_tools = Mock(return_value=mock_llm)

        registry = SkillRegistry(mock_llm, [], "skills")

        # 4. 从 Registry 获取 Skill
        registered_skill = registry.get_skill("code_review")
        assert registered_skill is not None
        assert registered_skill.id == skill.id

        # 5. 获取 LangChain Tools
        tools = registry.get_all_langchain_tools()
        assert len(tools) > 0

        # 6. 验证 Tool 属性
        code_review_tool = registry.get_langchain_tool("code_review")
        assert code_review_tool is not None
        assert code_review_tool.name == "code_review"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])