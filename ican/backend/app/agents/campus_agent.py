"""校园Agent：校园知识库 RAG 问答 / 活动推荐。"""
from app.agents.base import SpecialistAgent


class CampusAgent(SpecialistAgent):
    name = "campus"
    use_rag = True
