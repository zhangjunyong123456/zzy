"""求职Agent：简历优化 / 面试模拟（多轮）。"""
from app.agents.base import SpecialistAgent


class CareerAgent(SpecialistAgent):
    name = "career"
    use_rag = True  # 支持上传简历 PDF 后走 RAG
