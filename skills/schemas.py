"""Skill 数据模型定义"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_serializer
from langchain_core.tools import BaseTool


class SkillFrontmatter(BaseModel):
    """SKILL.md Frontmatter 数据模型（Claude Code 兼容）"""
    name: str = Field(..., description="Skill 唯一标识符")
    description: str = Field(..., description="Skill 功能描述（用于 LLM 匹配）")
    allowed_tools: Optional[str] = Field(
        None,
        alias="allowed-tools",
        description="允许使用的工具列表（逗号分隔）"
    )
    version: Optional[str] = Field("1.0.0", description="Skill 版本号")
    license: Optional[str] = Field(None, description="许可证类型")

    model_config = {
        "populate_by_name": True,
    }

    def get_allowed_tools(self) -> List[str]:
        """解析 allowed_tools 字符串为工具名称列表"""
        if not self.allowed_tools:
            return []
        return [tool.strip() for tool in self.allowed_tools.split(",") if tool.strip()]


class Skill(BaseModel):
    """完整的 Skill 数据模型"""
    frontmatter: SkillFrontmatter
    content: str = Field(..., description="SKILL.md 的 Markdown 内容")
    skill_path: str = Field(..., description="Skill 文件路径")
    scripts: Optional[List[str]] = Field(default_factory=list, description="可用脚本列表")
    references: Optional[List[str]] = Field(default_factory=list, description="参考文档列表")
    assets: Optional[List[str]] = Field(default_factory=list, description="资源文件列表")
    script_tools: Optional[List[BaseTool]] = Field(default_factory=list, exclude=True, description="从脚本转换的 LangChain Tools")

    @property
    def id(self) -> str:
        """Skill ID（从 frontmatter.name 派生）"""
        return self.frontmatter.name

    @property
    def full_id(self) -> str:
        """完整 ID（包含版本）"""
        return f"{self.frontmatter.name}@{self.frontmatter.version}"

    @property
    def all_tools(self) -> List[BaseTool]:
        """获取 Skill 的所有工具（脚本工具）"""
        return self.script_tools