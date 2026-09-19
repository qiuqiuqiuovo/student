"""教师管理：页面路由 + /api/teachers CRUD（与 students 同构）。

删除教师后其授课课程自动变为"未分配"（外键 ON DELETE SET NULL），
课程列表页对 teacher_name 为 NULL 的行显示"未分配"兜底文案。
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app import db, schemas
from app.deps import require_user_api, require_user_page
from app.templating import templates

router = APIRouter()


def _handle_db_error(exc: Exception) -> JSONResponse:
    code, detail = db.db_error_to_detail(exc)
    return JSONResponse({"detail": detail}, status_code=code)


@router.get("/teachers")
def teachers_page(request: Request, search: str = "", page: int = 1,
                  user=Depends(require_user_page)):
    return templates.TemplateResponse(request, "teachers.html", {
        "user": user, "search": search, **db.list_teachers(search, page, size=8),
    })


@router.get("/api/teachers")
def api_list_teachers(search: str = "", page: int = 1, size: int = 10,
                      user=Depends(require_user_api)):
    return db.list_teachers(search, page, size)


@router.post("/api/teachers", status_code=201)
def api_create_teacher(payload: schemas.TeacherIn, user=Depends(require_user_api)):
    try:
        new_id = db.create_teacher(payload.model_dump())
    except Exception as e:
        return _handle_db_error(e)
    return {"teacher_id": new_id}


@router.put("/api/teachers/{teacher_id}")
def api_update_teacher(teacher_id: int, payload: schemas.TeacherIn,
                       user=Depends(require_user_api)):
    try:
        ok = db.update_teacher(teacher_id, payload.model_dump())
    except Exception as e:
        return _handle_db_error(e)
    if not ok:
        return JSONResponse({"detail": "教师不存在"}, status_code=404)
    return {"ok": True}


@router.delete("/api/teachers/{teacher_id}")
def api_delete_teacher(teacher_id: int, user=Depends(require_user_api)):
    if not db.delete_teacher(teacher_id):
        return JSONResponse({"detail": "教师不存在"}, status_code=404)
    return {"ok": True}
