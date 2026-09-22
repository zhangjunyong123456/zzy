"""竞赛Agent：赛题分析 / 项目规划 / 技术路线 / 团队分工。"""
from app.agents.base import SpecialistAgent


class CompetitionAgent(SpecialistAgent):
    name = "competition"
    use_rag = False
