"""登录 / 注册 / 登出。

安全细节（面试点）：
- 登录失败不区分"用户名不存在"和"密码错误"，统一提示，防用户名枚举
- next 回跳参数只允许站内相对路径（以 / 开头且非 //），防开放重定向
- 登出用 POST 而非 GET：GET 会被 <img src="/logout"> 之类的跨站请求触发
"""
import pymysql
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db, security
from app.deps import get_session_user
from app.templating import templates

router = APIRouter()


def _safe_next(raw: str | None) -> str:
    """只允许站内相对路径，防开放重定向"""
    if raw and raw.startswith("/") and not raw.startswith("//"):
        return raw
    return "/"


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_session_user(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {
        "error": None, "registered": request.query_params.get("registered") == "1",
    })


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next_url: str = Form("", alias="next"),
):
    user = db.get_user_by_username(username.strip())
    if user is None or not security.verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(request, "login.html", {
            "error": "用户名或密码错误", "registered": False,
        }, status_code=400)
    request.session["user_id"] = user["user_id"]
    request.session["username"] = user["username"]
    return RedirectResponse(_safe_next(next_url), status_code=303)


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if get_session_user(request):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register")
def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm: str = Form(...),
    nickname: str = Form(""),
):
    username = username.strip()
    if len(username) < 3:
        return templates.TemplateResponse(request, "register.html", {
            "error": "用户名至少 3 个字符"}, status_code=400)
    if len(password) < 6:
        return templates.TemplateResponse(request, "register.html", {
            "error": "密码至少 6 位"}, status_code=400)
    if password != confirm:
        return templates.TemplateResponse(request, "register.html", {
            "error": "两次输入的密码不一致"}, status_code=400)
    try:
        db.create_user(username, security.hash_password(password), nickname.strip() or None)
    except pymysql.err.IntegrityError as e:
        if e.args[0] == 1062:
            return templates.TemplateResponse(request, "register.html", {
                "error": "用户名已被注册"}, status_code=409)
        raise
    return RedirectResponse("/login?registered=1", status_code=303)


@router.post("/logout")
def logout(request: Request, user=Depends(get_session_user)):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
