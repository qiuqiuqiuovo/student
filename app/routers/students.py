"""学生管理：页面路由 + /api/students CRUD。

页面与 API 共用 db.list_students 等同一套查询函数：
- 页面路由把结果直接交给模板做服务端渲染（搜索、分页走 URL 参数，curl 可验证）
- API 路由返回同样的 dict，由 FastAPI 自动序列化为 JSON
删除学生会级联删除其成绩（外键 ON DELETE CASCADE），前端确认框文案已明示。
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app import db, schemas
from app.deps import require_user_api, require_user_page
from app.templating import templates

router = APIRouter()


def _handle_db_error(exc: Exception) -> JSONResponse:
    """把 pymysql 异常翻译成 HTTP 响应（错误码语义见 db.db_error_to_detail）"""
    code, detail = db.db_error_to_detail(exc)
    return JSONResponse({"detail": detail}, status_code=code)


# ---------------------------------------------------------------
# 页面
# ---------------------------------------------------------------

@router.get("/students")
def students_page(request: Request, search: str = "", page: int = 1,
                  user=Depends(require_user_page)):
    return templates.TemplateResponse(request, "students.html", {
        "user": user, "search": search, **db.list_students(search, page, size=8),
    })


# ---------------------------------------------------------------
# API
# ---------------------------------------------------------------

@router.get("/api/students")
def api_list_students(search: str = "", page: int = 1, size: int = 10,
                      user=Depends(require_user_api)):
    return db.list_students(search, page, size)


@router.get("/api/students/options")
def api_student_options(user=Depends(require_user_api)):
    return db.student_options()


@router.post("/api/students", status_code=201)
def api_create_student(payload: schemas.StudentIn, user=Depends(require_user_api)):
    try:
        new_id = db.create_student(payload.model_dump())
    except Exception as e:
        return _handle_db_error(e)
    return {"student_id": new_id}


@router.put("/api/students/{student_id}")
def api_update_student(student_id: int, payload: schemas.StudentIn,
                       user=Depends(require_user_api)):
    if db.get_student(student_id) is None:
        return JSONResponse({"detail": "学生不存在"}, status_code=404)
    try:
        db.update_student(student_id, payload.model_dump())
    except Exception as e:
        return _handle_db_error(e)
    return {"ok": True}


@router.delete("/api/students/{student_id}")
def api_delete_student(student_id: int, user=Depends(require_user_api)):
    if not db.delete_student(student_id):
        return JSONResponse({"detail": "学生不存在"}, status_code=404)
    return {"ok": True}
