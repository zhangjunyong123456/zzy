"""主Agent：兜底通用回答。"""
from app.agents.base import SpecialistAgent


class MainAgent(SpecialistAgent):
    name = "main"
    use_rag = False
