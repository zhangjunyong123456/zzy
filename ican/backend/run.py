"""后端启动入口：用法 `python run.py`（需在 backend 目录下执行）。"""
import os
import sys

os.environ.setdefault("PYTHONUTF8", "1")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 将 .env 同步到真实环境变量（huggingface_hub 等库只读 os.environ，如 HF_ENDPOINT）
from dotenv import dotenv_values  # noqa: E402

for _k, _v in dotenv_values(".env").items():
    if _v is not None:
        os.environ.setdefault(_k, _v)

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
