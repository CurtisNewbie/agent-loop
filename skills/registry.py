"""Skill 注册和管理中心（SKILL.md → LangChain Tools）"""
from typing import Dict, List
from pathlib import Path
from langchain_core.tools import BaseTool
from skills.schemas import Skill
from skills.loader import SkillLoader
from skills.converter import skill_to_langchain_tool


class SkillRegistry:
    """Skill 注册和管理中心（SKILL.md → LangChain Tools）"""

    def __init__(self, llm, mcp_tools: List[BaseTool], skills_dir: str = "skills"):
        self.llm = llm
        self.mcp_tools = mcp_tools
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Skill] = {}
        self.langchain_tools: Dict[str, BaseTool] = {}

        # 自动加载所有 Skill 并转换为 LangChain Tools
        self.load_all()

    def load_all(self):
        """加载所有 Skill 并转换为 LangChain Tools"""
        if not self.skills_dir.exists():
            print(f"⚠ Skills directory not found: {self.skills_dir}")
            return

        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                try:
                    self.load_and_convert(skill_dir)
                except Exception as e:
                    print(f"✗ Failed to load skill {skill_dir.name}: {e}")

    def load_and_convert(self, skill_dir: Path) -> BaseTool:
        """加载 Skill 并转换为 LangChain Tool"""
        # 1. 加载 SKILL.md
        skill = SkillLoader.load(str(skill_dir))
        
        # 2. 注册原始 Skill
        self.register(skill)
        
        # 3. 转换为 LangChain Tool
        langchain_tool = skill_to_langchain_tool(skill, self.llm, self.mcp_tools)
        self.langchain_tools[skill.id] = langchain_tool
        
        print(f"✓ Skill converted to LangChain Tool: {skill.id} v{skill.frontmatter.version}")
        return langchain_tool

    def register(self, skill: Skill):
        """注册原始 Skill"""
        self.skills[skill.id] = skill

    def get_skill(self, skill_id: str) -> Skill:
        """获取原始 Skill"""
        return self.skills.get(skill_id)

    def get_langchain_tool(self, skill_id: str) -> BaseTool:
        """获取 LangChain Tool"""
        return self.langchain_tools.get(skill_id)

    def get_all_langchain_tools(self) -> List[BaseTool]:
        """获取所有 Skills 作为 LangChain Tools"""
        return list(self.langchain_tools.values())

    def list_skills(self) -> List[Skill]:
        """列出所有 Skill"""
        return list(self.skills.values())

    def reload(self, skill_id: str):
        """热重载 Skill"""
        if skill_id not in self.skills:
            raise ValueError(f"Skill not found: {skill_id}")

        skill_dir = Path(self.skills[skill_id].skill_path)
        new_tool = self.load_and_convert(skill_dir)
        print(f"✓ Skill reloaded: {skill_id}")

    def get_tools_by_skill_ids(self, skill_ids: List[str]) -> List[BaseTool]:
        """
        根据 Skill ID 列表获取对应的 LangChain Tools

        Args:
            skill_ids: Skill ID 列表

        Returns:
            LangChain Tools 列表
        """
        return [
            self.langchain_tools[skill_id]
            for skill_id in skill_ids
            if skill_id in self.langchain_tools
        ]

    def get_skills_by_ids(self, skill_ids: List[str]) -> List[Skill]:
        """
        根据 Skill ID 列表获取对应的 Skill 对象

        Args:
            skill_ids: Skill ID 列表

        Returns:
            Skill 对象列表
        """
        return [
            self.skills[skill_id]
            for skill_id in skill_ids
            if skill_id in self.skills
        ]