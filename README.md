# 🎯 Skill System

Agent技能注册和管理系统，受anthropics/skills启发。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/License-MIT-yellow" />
</p>

## ✨ 特性

- 📝 技能注册和管理
- 🔍 技能搜索和发现
- 📂 分类和标签系统
- 📊 使用统计
- 🔌 动态加载插件
- 🛠️ OpenAI工具格式支持

## 🚀 快速开始

```bash
python skill_registry.py
```

## 📖 使用示例

```python
from skill_registry import create_default_registry, Skill

# 创建注册中心
registry = create_default_registry()

# 注册自定义技能
registry.register_function(
    name="weather",
    description="查询天气",
    func=lambda city: f"{city}天气: 晴天 25°C",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名"}
        },
        "required": ["city"]
    },
    category="utility",
    tags=["weather", "query"]
)

# 执行技能
result = registry.execute("weather", city="北京")

# 搜索技能
results = registry.search("time")

# 列出所有技能
skills = registry.list_skills(category="utility")

# 获取OpenAI工具配置
tools = registry.get_tools_config()

# 统计信息
stats = registry.get_stats()
```

## 📂 技能目录结构

```
skills/
├── __init__.py
├── utility.py       # 实用工具技能
├── web.py           # 网络相关技能
├── file.py          # 文件操作技能
└── custom.py        # 自定义技能
```

每个技能文件可以定义：
```python
SKILL = {
    "name": "my_skill",
    "description": "我的技能",
    "func": my_function,
    "parameters": {...}
}
```

## 📁 项目结构

```
skill-system/
├── skill_registry.py  # 技能注册中心
├── skills/            # 技能插件目录
├── registry.json      # 注册信息持久化
└── README.md
```

## 📄 许可证

MIT License
