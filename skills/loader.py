"""SKILL.md 文件加载器"""
import re
import importlib.util
import inspect
from pathlib import Path
from typing import List, Optional, Any, Callable
from skills.schemas import Skill, SkillFrontmatter
from langchain_core.tools import BaseTool, StructuredTool


class SkillLoader:
    """加载 SKILL.md 文件并解析为 Skill 对象"""

    @staticmethod
    def load(skill_path: str) -> Skill:
        """加载单个 Skill（包括脚本工具）"""
        skill_dir = Path(skill_path)
        skill_md_path = skill_dir / "SKILL.md"

        if not skill_md_path.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        # 读取 SKILL.md 内容
        content = skill_md_path.read_text(encoding="utf-8")

        # 解析 Frontmatter 和内容
        frontmatter, markdown_content = SkillLoader._parse_skill_md(content)

        # 发现附加资源
        scripts = SkillLoader._discover_directory(skill_dir / "scripts")
        references = SkillLoader._discover_directory(skill_dir / "references")
        assets = SkillLoader._discover_directory(skill_dir / "assets")

        # 发现并加载脚本工具
        script_tools = SkillLoader._load_script_tools(skill_dir)

        return Skill(
            frontmatter=frontmatter,
            content=markdown_content,
            skill_path=str(skill_dir),
            scripts=scripts,
            references=references,
            assets=assets,
            script_tools=script_tools
        )

    @staticmethod
    def _load_script_tools(skill_dir: Path) -> List[BaseTool]:
        """
        加载并转换 Skill 脚本为 LangChain Tools

        支持两种格式：
        1. @tool 装饰器：显式标记的函数
        2. 规范命名：{skill_name}_{script_name}_{function_name}
        """
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists():
            return []

        tools: List[BaseTool] = []
        skill_name = skill_dir.name

        # 遍历所有 Python 脚本
        for script_file in scripts_dir.glob("*.py"):
            if script_file.name.startswith("_"):
                continue  # 跳过私有文件

            try:
                module_tools = SkillLoader._load_module_tools(script_file, skill_name)
                tools.extend(module_tools)
            except Exception as e:
                print(f"⚠ Failed to load tools from {script_file.name}: {e}")

        return tools

    @staticmethod
    def _load_module_tools(script_file: Path, skill_name: str) -> List[BaseTool]:
        """从单个 Python 模块加载工具"""
        module_name = f"skill_{skill_name}_{script_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, script_file)

        if spec is None or spec.loader is None:
            return []

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        tools: List[BaseTool] = []

        # 遍历模块中的所有成员
        for name, obj in inspect.getmembers(module):
            # 跳过私有成员
            if name.startswith("_"):
                continue

            # 格式 1: @tool 装饰器（已经是 BaseTool 实例）
            if isinstance(obj, BaseTool):
                tools.append(obj)

            # 格式 2: 规范命名的函数（转换为 StructuredTool）
            elif inspect.isfunction(obj) and not inspect.ismethod(obj):
                # 检查命名规范：
                # - {skill_name}_{function_name}
                # - {skill_name}_{script_name}_{function_name}
                # 例如: code_review_security_check 或 code_review_linter_security_check
                if name.startswith(skill_name + "_"):
                    tool = SkillLoader._function_to_tool(obj, name)
                    tools.append(tool)

        return tools

    @staticmethod
    def _function_to_tool(func: Callable, tool_name: str) -> StructuredTool:
        """将函数转换为 StructuredTool"""
        # 获取函数签名和文档字符串
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or f"Tool: {tool_name}"

        # 提取描述（第一行）
        description = doc.split("\n")[0] if doc else f"Tool: {tool_name}"

        # 创建参数 schema
        args_schema = SkillLoader._create_args_schema(sig, doc)

        return StructuredTool(
            name=tool_name,
            description=description,
            args_schema=args_schema,
            func=func,
            coroutine=func if inspect.iscoroutinefunction(func) else None
        )

    @staticmethod
    def _create_args_schema(sig: inspect.Signature, doc: str) -> type:
        """从函数签名创建 Pydantic BaseModel"""
        from pydantic import BaseModel, Field, create_model

        # 构建字段字典
        fields = {}
        param_docs = SkillLoader._parse_param_docs(doc)

        for param_name, param in sig.parameters.items():
            # 获取参数类型，优先使用 annotation
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                param_type = str
            elif isinstance(param_type, str):
                # 将字符串类型转换为实际类型
                param_type = str  # 简化处理，实际可以更复杂

            default = param.default
            description = param_docs.get(param_name, "")

            # 处理默认值
            if default is inspect.Parameter.empty:
                # 必需参数
                fields[param_name] = (param_type, Field(description=description))
            else:
                # 可选参数
                fields[param_name] = (param_type, Field(default=default, description=description))

        # 使用 create_model 动态创建
        return create_model("ToolArgs", **fields)

    @staticmethod
    def _parse_param_docs(doc: str) -> dict[str, str]:
        """从文档字符串中解析参数描述"""
        param_docs = {}
        if not doc:
            return param_docs

        lines = doc.split("\n")
        current_param = None

        for line in lines:
            line = line.strip()
            if line.startswith("Args:"):
                continue
            elif line.startswith("- ") or line.startswith("  "):
                # 尝试提取参数名和描述
                parts = line.lstrip("- ").split(":", 1)
                if len(parts) == 2:
                    param_name = parts[0].strip()
                    param_desc = parts[1].strip()
                    param_docs[param_name] = param_desc

        return param_docs

    @staticmethod
    def _parse_skill_md(content: str) -> tuple[SkillFrontmatter, str]:
        """解析 SKILL.md，分离 Frontmatter 和内容"""
        # 匹配 YAML Frontmatter（--- 包围）
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            raise ValueError("Invalid SKILL.md format: missing frontmatter")

        yaml_content = match.group(1)
        markdown_content = match.group(2)

        # 解析 YAML Frontmatter
        import yaml
        frontmatter_dict = yaml.safe_load(yaml_content)
        frontmatter = SkillFrontmatter(**frontmatter_dict)

        return frontmatter, markdown_content

    @staticmethod
    def _discover_directory(dir_path: Path) -> List[str]:
        """发现目录中的文件"""
        if not dir_path.exists():
            return []

        return [str(f) for f in dir_path.iterdir() if f.is_file()]