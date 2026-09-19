"""FastAPI 应用装配入口。

启动方式（在项目根目录执行）：
    venv/Scripts/python -m uvicorn app.main:app --port 8000

访问：
    页面   http://127.0.0.1:8000/
    接口文档 http://127.0.0.1:8000/docs（FastAPI 自动生成的 Swagger UI）
"""
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import config
from app.deps import UnauthorizedError
from app.routers import auth, courses, grades, stats, students, teachers
from app.templating import BASE_DIR, templates

app = FastAPI(title="学生成绩管理系统", version="1.0.0")

# 签名 Cookie 会话：session 只存 user_id / username（itsdangerous 签名，4KB 上限）
# same_site="lax" + 状态变更全走 JSON fetch + 登出走 POST，演示项目因此不做 CSRF token
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    max_age=86400,
    same_site="lax",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.exception_handler(UnauthorizedError)
async def unauth_handler(request: Request, exc: UnauthorizedError):
    """未登录统一分流：页面 → 302 到登录页（带 next 回跳）；API → 401 JSON"""
    if request.url.path.startswith("/api"):
        return JSONResponse({"detail": "未登录或会话已过期"}, status_code=401)
    return RedirectResponse(f"/login?next={quote(exc.next_url)}", status_code=302)


app.include_router(auth.router)
app.include_router(students.router)
app.include_router(teachers.router)
app.include_router(courses.router)
app.include_router(grades.router)
app.include_router(stats.router)
