"""登录态依赖注入。

统一策略（见 main.py 的异常处理器）：
- 页面路由依赖 require_user_page：未登录 → 302 重定向到 /login?next=原地址
- API 路由依赖 require_user_api：未登录 → 401 JSON（前端 fetchJSON 收到后跳转登录页）
同一个 UnauthorizedError 异常，按请求路径分流成两种响应，一个处理器搞定。
"""
from fastapi import Request

from app.db import get_user_by_id


class UnauthorizedError(Exception):
    def __init__(self, next_url: str = "/"):
        self.next_url = next_url
        super().__init__("未登录")


def get_session_user(request: Request) -> dict | None:
    """从签名 session cookie 中取出 user_id 并回查数据库。

    每次请求都回查 users 表（而非只信 cookie）：
    用户被删除后其旧会话立即失效——session 里只存 user_id，正文仍以数据库为准。
    """
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return get_user_by_id(user_id)


def require_user_api(request: Request) -> dict:
    user = get_session_user(request)
    if user is None:
        raise UnauthorizedError()
    return user


def require_user_page(request: Request) -> dict:
    user = get_session_user(request)
    if user is None:
        raise UnauthorizedError(next_url=request.url.path)
    return user
