"""科研Agent：文献结构化分析 / 论文摘要。"""
from app.agents.base import SpecialistAgent


class ResearchAgent(SpecialistAgent):
    name = "research"
    use_rag = True
