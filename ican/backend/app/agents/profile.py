"""用户画像 → 提示词文本块。游客返回空串（零行为变化）。"""
from app.services.user_service import PROFILE_FIELDS

_LABELS = {
    "nickname": "昵称",
    "major": "专业",
    "grade": "年级",
    "interests": "兴趣爱好",
    "experience": "经历/背景",
    "goal": "发展目标",
}


def build_profile_text(user: dict | None) -> str:
    if not user:
        return ""
    lines = [
        f"- {_LABELS[k]}：{user[k]}"
        for k in PROFILE_FIELDS
        if (user.get(k) or "").strip()
    ]
    if not lines:
        return ""
    return (
        "【用户画像】请结合以下用户信息个性化你的回答"
        "（自然融入即可，不要复述或逐条解释）：\n" + "\n".join(lines)
    )
