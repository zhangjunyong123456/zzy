"""Agent 元数据：前端展示用的名称/图标/主题色（单一事实来源）。"""

AGENT_META: dict[str, dict[str, str]] = {
    "study": {"label": "学习Agent", "icon": "📚", "color": "#E8896B"},
    "research": {"label": "科研Agent", "icon": "🔬", "color": "#93AB84"},
    "competition": {"label": "竞赛Agent", "icon": "🏆", "color": "#DFA453"},
    "career": {"label": "求职Agent", "icon": "💼", "color": "#86AD72"},
    "campus": {"label": "校园Agent", "icon": "🏫", "color": "#7FB39C"},
    "main": {"label": "主Agent", "icon": "🧭", "color": "#D9694A"},
}
