"""成绩管理：录入（双重校验）/ 编辑 / 删除 / 批量导入（事务）。

双重校验的两层防线（面试点）：
- 第一层 应用层：schemas.GradeIn 的 pydantic 校验（score 0-100、必填字段），
  非法数据在进入 SQL 前就被 422 拦截
- 第二层 数据库层：04_advanced.sql 里的 BEFORE INSERT/UPDATE 触发器 + CHECK 约束，
  即使绕过应用直连 MySQL 插入 150 分，也会被 SIGNAL 拒绝
批量导入：逐行调用存储过程 sp_insert_grade，整个批次包在一个事务里，
任一行失败则全部回滚（对应 05_transaction_demo.sql 的演示二）。
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


# ---------------------------------------------------------------
# 页面
# ---------------------------------------------------------------

@router.get("/grades")
def grades_page(request: Request, student_id: int = 0, course_id: int = 0,
                page: int = 1, user=Depends(require_user_page)):
    return templates.TemplateResponse(request, "grades.html", {
        "user": user,
        "student_id": student_id, "course_id": course_id,
        **db.list_grades(student_id or None, course_id or None, page, size=8),
        "student_options": db.student_options(),
        "course_options": db.course_options(),
    })


# ---------------------------------------------------------------
# API：单条 CRUD
# ---------------------------------------------------------------

@router.get("/api/grades")
def api_list_grades(student_id: int = 0, course_id: int = 0,
                    page: int = 1, size: int = 10,
                    user=Depends(require_user_api)):
    return db.list_grades(student_id or None, course_id or None, page, size)


@router.post("/api/grades", status_code=201)
def api_create_grade(payload: schemas.GradeIn, user=Depends(require_user_api)):
    # 显式检查外键存在性：给出比 MySQL 外键报错更友好的提示
    if db.get_student(payload.student_id) is None:
        return JSONResponse({"detail": "学生不存在"}, status_code=404)
    if db.get_course(payload.course_id) is None:
        return JSONResponse({"detail": "课程不存在"}, status_code=404)
    try:
        new_id = db.create_grade(payload.model_dump())
    except Exception as e:
        # 1062（同学生同课程同日期已存在）→ 409；1644（触发器拒绝）→ 400
        return _handle_db_error(e)
    return {"grade_id": new_id}


@router.put("/api/grades/{grade_id}")
def api_update_grade(grade_id: int, payload: schemas.GradeUpdateIn,
                     user=Depends(require_user_api)):
    try:
        ok = db.update_grade(grade_id, payload.model_dump())
    except Exception as e:
        return _handle_db_error(e)
    if not ok:
        return JSONResponse({"detail": "成绩记录不存在"}, status_code=404)
    return {"ok": True}


@router.delete("/api/grades/{grade_id}")
def api_delete_grade(grade_id: int, user=Depends(require_user_api)):
    if not db.delete_grade(grade_id):
        return JSONResponse({"detail": "成绩记录不存在"}, status_code=404)
    return {"ok": True}


# ---------------------------------------------------------------
# API：批量导入（单事务，一行失败全部回滚）
# ---------------------------------------------------------------

@router.post("/api/grades/batch")
def api_batch_grades(payload: schemas.GradeBatchIn, user=Depends(require_user_api)):
    """批量导入格式：每行 "学号,课程号,分数,考试日期"，逐行调用存储过程。

    与 get_conn 的约定：任一行失败 → 手动 rollback 整个事务后返回错误，
    已成功的行一并撤销（原子性）；全部成功 → 正常退出，get_conn 统一 commit。
    """
    with db.get_conn() as conn:
        for i, row in enumerate(payload.rows, start=1):
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "CALL sp_insert_grade(%s, %s, %s, %s)",
                        (row.student_no, row.course_no, row.score, row.exam_date),
                    )
            except Exception as e:
                conn.rollback()  # 一行失败：整个批次回滚
                code, detail = db.db_error_to_detail(e)
                return JSONResponse(
                    {"detail": f"第 {i} 行失败，整个批次已回滚：{detail}"},
                    status_code=code,
                )
    return {"ok": True, "count": len(payload.rows)}
