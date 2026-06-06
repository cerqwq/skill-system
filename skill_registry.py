"""
Skill System - Agent技能注册和管理系统
受 anthropics/skills 启发，支持技能发现、加载、执行
"""

import json
import os
import sys
import importlib
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class Skill:
    """技能定义"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    enabled: bool = True

    # 运行时属性
    func: Optional[Callable] = None
    source_file: Optional[str] = None
    usage_count: int = 0
    last_used: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "category": self.category,
            "tags": self.tags,
            "parameters": self.parameters,
            "examples": self.examples,
            "enabled": self.enabled,
            "usage_count": self.usage_count,
            "last_used": self.last_used
        }

    def to_openai_tool(self) -> Dict:
        """转换为OpenAI工具格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class SkillRegistry:
    """
    技能注册中心
    支持：技能注册、发现、加载、执行
    """

    def __init__(self, skills_dir: str = None):
        self.skills: Dict[str, Skill] = {}
        self.skills_dir = Path(skills_dir) if skills_dir else Path(__file__).parent / "skills"
        self.categories: Dict[str, List[str]] = {}

    def register(self, skill: Skill):
        """注册技能"""
        if skill.name in self.skills:
            print(f"[警告] 技能 '{skill.name}' 已存在，将被覆盖")

        self.skills[skill.name] = skill

        # 更新分类索引
        if skill.category not in self.categories:
            self.categories[skill.category] = []
        if skill.name not in self.categories[skill.category]:
            self.categories[skill.category].append(skill.name)

        print(f"[技能] 已注册: {skill.name} (v{skill.version})")

    def register_function(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters: Dict = None,
        category: str = "general",
        tags: List[str] = None,
        **kwargs
    ):
        """注册函数为技能"""
        skill = Skill(
            name=name,
            description=description,
            func=func,
            parameters=parameters or {},
            category=category,
            tags=tags or [],
            **kwargs
        )
        self.register(skill)

    def unregister(self, name: str):
        """注销技能"""
        if name in self.skills:
            skill = self.skills.pop(name)
            if skill.category in self.categories:
                self.categories[skill.category] = [
                    n for n in self.categories[skill.category] if n != name
                ]
            print(f"[技能] 已注销: {name}")

    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(name)

    def execute(self, name: str, **kwargs) -> str:
        """执行技能"""
        skill = self.skills.get(name)
        if not skill:
            return f"技能不存在: {name}"

        if not skill.enabled:
            return f"技能已禁用: {name}"

        if not skill.func:
            return f"技能未实现: {name}"

        try:
            result = skill.func(**kwargs)
            skill.usage_count += 1
            skill.last_used = datetime.now().isoformat()
            return str(result)
        except Exception as e:
            return f"技能执行失败: {e}"

    def list_skills(self, category: str = None, enabled_only: bool = True) -> List[Dict]:
        """列出技能"""
        skills = []
        for skill in self.skills.values():
            if enabled_only and not skill.enabled:
                continue
            if category and skill.category != category:
                continue
            skills.append(skill.to_dict())
        return skills

    def list_categories(self) -> List[str]:
        """列出所有分类"""
        return list(self.categories.keys())

    def search(self, query: str) -> List[Skill]:
        """搜索技能"""
        query_lower = query.lower()
        results = []

        for skill in self.skills.values():
            # 名称匹配
            if query_lower in skill.name.lower():
                results.append(skill)
                continue

            # 描述匹配
            if query_lower in skill.description.lower():
                results.append(skill)
                continue

            # 标签匹配
            if any(query_lower in tag.lower() for tag in skill.tags):
                results.append(skill)
                continue

        return results

    def get_tools_config(self) -> List[Dict]:
        """获取OpenAI格式的工具配置"""
        return [
            skill.to_openai_tool()
            for skill in self.skills.values()
            if skill.enabled and skill.func
        ]

    def load_from_directory(self, directory: str = None):
        """从目录加载技能"""
        load_dir = Path(directory) if directory else self.skills_dir

        if not load_dir.exists():
            print(f"[技能] 目录不存在: {load_dir}")
            return

        for file_path in load_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            try:
                self._load_skill_module(file_path)
            except Exception as e:
                print(f"[技能] 加载失败 {file_path.name}: {e}")

    def _load_skill_module(self, file_path: Path):
        """加载技能模块"""
        module_name = file_path.stem

        # 动态导入
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # 查找SKILL定义
        if hasattr(module, 'SKILL'):
            skill_def = module.SKILL
            if isinstance(skill_def, dict):
                skill = Skill(
                    name=skill_def.get('name', module_name),
                    description=skill_def.get('description', ''),
                    version=skill_def.get('version', '1.0.0'),
                    author=skill_def.get('author', ''),
                    category=skill_def.get('category', 'general'),
                    tags=skill_def.get('tags', []),
                    parameters=skill_def.get('parameters', {}),
                    examples=skill_def.get('examples', []),
                    func=skill_def.get('func'),
                    source_file=str(file_path)
                )
                self.register(skill)

        # 查找所有以_skill结尾的函数
        for attr_name in dir(module):
            if attr_name.endswith('_skill'):
                func = getattr(module, attr_name)
                if callable(func):
                    skill_name = attr_name.replace('_skill', '')
                    self.register_function(
                        name=skill_name,
                        description=func.__doc__ or f"技能: {skill_name}",
                        func=func,
                        source_file=str(file_path)
                    )

    def save_registry(self, path: str = None):
        """保存注册信息"""
        save_path = Path(path) if path else self.skills_dir / "registry.json"
        save_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "skills": {name: skill.to_dict() for name, skill in self.skills.items()},
            "categories": self.categories,
            "updated_at": datetime.now().isoformat()
        }

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_registry(self, path: str = None):
        """加载注册信息"""
        load_path = Path(path) if path else self.skills_dir / "registry.json"

        if not load_path.exists():
            return

        with open(load_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.categories = data.get('categories', {})

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_skills": len(self.skills),
            "enabled_skills": sum(1 for s in self.skills.values() if s.enabled),
            "categories": len(self.categories),
            "total_usage": sum(s.usage_count for s in self.skills.values())
        }


# 内置技能示例
def echo_skill(text: str) -> str:
    """回显文本"""
    return text

def timestamp_skill() -> str:
    """获取当前时间戳"""
    return datetime.now().isoformat()

def json_format_skill(text: str) -> str:
    """格式化JSON"""
    try:
        data = json.loads(text)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as e:
        return f"JSON格式错误: {e}"


def create_default_registry(**kwargs) -> SkillRegistry:
    """创建带有默认技能的注册中心"""
    registry = SkillRegistry(**kwargs)

    # 注册内置技能
    registry.register_function(
        name="echo",
        description="回显输入的文本",
        func=echo_skill,
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要回显的文本"}
            },
            "required": ["text"]
        },
        category="utility",
        tags=["echo", "text", "utility"]
    )

    registry.register_function(
        name="timestamp",
        description="获取当前时间戳",
        func=timestamp_skill,
        parameters={"type": "object", "properties": {}},
        category="utility",
        tags=["time", "timestamp"]
    )

    registry.register_function(
        name="json_format",
        description="格式化JSON字符串",
        func=json_format_skill,
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "JSON字符串"}
            },
            "required": ["text"]
        },
        category="utility",
        tags=["json", "format", "utility"]
    )

    # 尝试从目录加载更多技能
    registry.load_from_directory()

    return registry


if __name__ == "__main__":
    registry = create_default_registry()

    print("Skill System 已启动")
    print(f"统计: {registry.get_stats()}")
    print()

    while True:
        try:
            cmd = input("命令 (list/search/exec/quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not cmd:
            continue
        if cmd.lower() in ("quit", "exit"):
            break

        if cmd == "list":
            skills = registry.list_skills()
            for s in skills:
                print(f"  {s['name']}: {s['description']}")

        elif cmd.startswith("search "):
            query = cmd[7:]
            results = registry.search(query)
            print(f"找到 {len(results)} 个技能:")
            for s in results:
                print(f"  {s.name}: {s.description}")

        elif cmd.startswith("exec "):
            parts = cmd[5:].split(" ", 1)
            skill_name = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            if args:
                result = registry.execute(skill_name, text=args)
            else:
                result = registry.execute(skill_name)
            print(f"结果: {result}")

        else:
            print("未知命令")

        print()
