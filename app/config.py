"""应用配置：数据库连接与 Session 签名密钥。

配置优先级：环境变量 > 项目根目录 .env 文件 > 默认值。
用户可在项目根目录创建 .env（已在 .gitignore 中排除，不会提交到 git）：

    SCORE_DB_PASSWORD=你的MySQL密码
    SCORE_DB_SECRET_KEY=一串随机字符串
"""
import os
from pathlib import Path


def _load_env() -> None:
    """简易 .env 读取（不引入 python-dotenv 依赖）"""
    path = Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()

DB_HOST = os.getenv("SCORE_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("SCORE_DB_PORT", "3306"))
DB_USER = os.getenv("SCORE_DB_USER", "root")
DB_PASSWORD = os.getenv("SCORE_DB_PASSWORD", "")
DB_NAME = os.getenv("SCORE_DB_NAME", "score_db")

# Session 签名密钥：换掉它会令所有已登录会话失效（演示项目用默认值即可）
SECRET_KEY = os.getenv("SCORE_DB_SECRET_KEY", "score-db-dev-secret-key")
