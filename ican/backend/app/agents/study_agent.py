"""学习Agent：PDF RAG 问答 / AI 笔记（重点·难点·考点）。"""
from app.agents.base import SpecialistAgent


class StudyAgent(SpecialistAgent):
    name = "study"
    use_rag = True
