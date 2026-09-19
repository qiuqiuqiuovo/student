"""数据库访问层：pymysql 连接管理 + 各实体查询函数。

设计说明（面试点）：
- 刻意使用裸 SQL 而非 ORM：SQL 能力是本项目的卖点之一，裸 SQL 能精确控制
  每条语句与索引的配合，也方便在面试中逐条讲解
- 每请求新开连接（当前规模足够）；生产环境可换连接池（如 DBUtils），
  这是"连接建立开销 vs 连接复用"的经典权衡
- 所有值一律 %s 参数化占位，杜绝 SQL 注入；
  WHERE/ORDER BY 等结构片段不可参数化，仅由代码内部常量拼接（见 list_* 函数）
- 排序字段不能参数化，因此本层不提供任意排序；如要加，需先过字段白名单映射
"""
import math
from contextlib import contextmanager

import pymysql
from app import config


@contextmanager
def get_conn():
    """获取数据库连接：正常退出自动 commit，异常自动 rollback。

    三个关键参数：
    - cursorclass=DictCursor：查询结果以 dict 列表返回（否则是元组，字段序易错）
    - charset="utf8mb4"：与库/表字符集一致，中文不丢不乱
    - autocommit=False：由本 context manager 统一控制提交时机，
      忘记 commit 是"数据没写进去"最常见的原因
    """
    conn = pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def db_error_to_detail(exc: Exception) -> tuple[int, str]:
    """把 pymysql 异常映射为 (HTTP 状态码, 用户可读消息)。

    错误码速查（面试点）：
    - 1062 唯一键冲突（IntegrityError）
    - 1452 外键约束失败，关联记录不存在（IntegrityError）
    - 1644 触发器 SIGNAL 主动抛出的业务错误（OperationalError）
    - 3819 CHECK 约束违反（OperationalError）
    """
    if isinstance(exc, pymysql.err.IntegrityError):
        if exc.args[0] == 1062:
            return 409, "数据已存在（唯一键冲突）"
        if exc.args[0] == 1452:
            return 404, "关联的学生或课程不存在（外键约束）"
        return 409, f"数据完整性约束冲突（错误码 {exc.args[0]}）"
    if isinstance(exc, pymysql.err.OperationalError):
        if exc.args[0] == 1644:
            # 触发器 SIGNAL 的中文业务报错，原样透传给用户（双重校验的第二层）
            return 400, exc.args[1]
        if exc.args[0] == 3819:
            return 400, f"违反 CHECK 约束：{exc.args[1]}"
    return 500, "数据库操作失败"


# ---------------------------------------------------------------
# 用户
# ---------------------------------------------------------------

def get_user_by_username(username: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, username, password_hash, nickname, created_at "
                "FROM users WHERE username = %s",
                (username,),
            )
            return cur.fetchone()


def get_user_by_id(user_id: int) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, username, password_hash, nickname, created_at "
                "FROM users WHERE user_id = %s",
                (user_id,),
            )
            return cur.fetchone()


def create_user(username: str, password_hash: str, nickname: str | None) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, nickname) VALUES (%s, %s, %s)",
                (username, password_hash, nickname),
            )


# ---------------------------------------------------------------
# 学生
# ---------------------------------------------------------------

_STUDENT_SEARCH_SQL = (
    "WHERE student_no LIKE %s OR name LIKE %s OR major LIKE %s OR class_name LIKE %s"
)


def list_students(search: str = "", page: int = 1, size: int = 10) -> dict:
    """学生列表（搜索 + 分页）。

    注意：LIKE '%关键词%' 的前缀通配符无法使用 B-Tree 索引（全表扫描），
    数据量大时应换全文索引（ngram 分词）或搜索引擎——本系统数据量小，直接 LIKE。
    """
    page = max(1, page)
    size = min(max(1, size), 100)
    where, params = "", []
    if search:
        where = _STUDENT_SEARCH_SQL
        kw = f"%{search}%"
        params = [kw, kw, kw, kw]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total FROM students {where}", params)
            total = cur.fetchone()["total"]
            cur.execute(
                f"SELECT * FROM students {where} ORDER BY student_id DESC "
                f"LIMIT %s OFFSET %s",
                params + [size, (page - 1) * size],
            )
            items = cur.fetchall()
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, math.ceil(total / size)) if total else 1,
    }


def get_student(student_id: int) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
            return cur.fetchone()


def create_student(data: dict) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO students (student_no, name, gender, birth_date, major, "
                "class_name, enrollment_date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    data["student_no"], data["name"], data["gender"],
                    data["birth_date"], data["major"], data["class_name"],
                    data["enrollment_date"],
                ),
            )
            return cur.lastrowid


def update_student(student_id: int, data: dict) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE students SET student_no = %s, name = %s, gender = %s, "
                "birth_date = %s, major = %s, class_name = %s, enrollment_date = %s "
                "WHERE student_id = %s",
                (
                    data["student_no"], data["name"], data["gender"],
                    data["birth_date"], data["major"], data["class_name"],
                    data["enrollment_date"], student_id,
                ),
            )
            return cur.rowcount > 0


def delete_student(student_id: int) -> bool:
    # 级联说明：外键 ON DELETE CASCADE 会同时删除该学生的全部成绩记录
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
            return cur.rowcount > 0


def student_options() -> list[dict]:
    """学生下拉选项（成绩录入表单用）"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT student_id, student_no, name, class_name "
                "FROM students ORDER BY student_no"
            )
            return cur.fetchall()


# ---------------------------------------------------------------
# 教师
# ---------------------------------------------------------------

def list_teachers(search: str = "", page: int = 1, size: int = 10) -> dict:
    page = max(1, page)
    size = min(max(1, size), 100)
    where, params = "", []
    if search:
        where = (
            "WHERE teacher_no LIKE %s OR name LIKE %s OR title LIKE %s "
            "OR department LIKE %s OR phone LIKE %s"
        )
        kw = f"%{search}%"
        params = [kw] * 5
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total FROM teachers {where}", params)
            total = cur.fetchone()["total"]
            cur.execute(
                f"SELECT * FROM teachers {where} ORDER BY teacher_id DESC "
                f"LIMIT %s OFFSET %s",
                params + [size, (page - 1) * size],
            )
            items = cur.fetchall()
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, math.ceil(total / size)) if total else 1,
    }


def create_teacher(data: dict) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO teachers (teacher_no, name, gender, title, department, phone) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    data["teacher_no"], data["name"], data["gender"],
                    data["title"], data["department"], data["phone"],
                ),
            )
            return cur.lastrowid


def update_teacher(teacher_id: int, data: dict) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE teachers SET teacher_no = %s, name = %s, gender = %s, "
                "title = %s, department = %s, phone = %s WHERE teacher_id = %s",
                (
                    data["teacher_no"], data["name"], data["gender"],
                    data["title"], data["department"], data["phone"], teacher_id,
                ),
            )
            return cur.rowcount > 0


def delete_teacher(teacher_id: int) -> bool:
    # 级联说明：外键 ON DELETE SET NULL 会让相关课程的授课教师变为"未分配"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM teachers WHERE teacher_id = %s", (teacher_id,))
            return cur.rowcount > 0


# ---------------------------------------------------------------
# 课程
# ---------------------------------------------------------------

def list_courses(search: str = "", page: int = 1, size: int = 10) -> dict:
    page = max(1, page)
    size = min(max(1, size), 100)
    where, params = "", []
    if search:
        where = "WHERE c.course_no LIKE %s OR c.course_name LIKE %s OR t.name LIKE %s"
        kw = f"%{search}%"
        params = [kw, kw, kw]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) AS total FROM courses c "
                f"LEFT JOIN teachers t ON c.teacher_id = t.teacher_id {where}",
                params,
            )
            total = cur.fetchone()["total"]
            cur.execute(
                f"SELECT c.*, t.name AS teacher_name FROM courses c "
                f"LEFT JOIN teachers t ON c.teacher_id = t.teacher_id {where} "
                f"ORDER BY c.course_id DESC LIMIT %s OFFSET %s",
                params + [size, (page - 1) * size],
            )
            items = cur.fetchall()
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, math.ceil(total / size)) if total else 1,
    }


def get_course(course_id: int) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM courses WHERE course_id = %s", (course_id,))
            return cur.fetchone()


def create_course(data: dict) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO courses (course_no, course_name, credits, teacher_id, semester) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    data["course_no"], data["course_name"], data["credits"],
                    data["teacher_id"], data["semester"],
                ),
            )
            return cur.lastrowid


def update_course(course_id: int, data: dict) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE courses SET course_no = %s, course_name = %s, credits = %s, "
                "teacher_id = %s, semester = %s WHERE course_id = %s",
                (
                    data["course_no"], data["course_name"], data["credits"],
                    data["teacher_id"], data["semester"], course_id,
                ),
            )
            return cur.rowcount > 0


def delete_course(course_id: int) -> bool:
    # 级联说明：外键 ON DELETE CASCADE 会同时删除该课程的全部成绩记录
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
            return cur.rowcount > 0


def course_options() -> list[dict]:
    """课程下拉选项（成绩录入表单用）"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.course_id, c.course_no, c.course_name, t.name AS teacher_name "
                "FROM courses c LEFT JOIN teachers t ON c.teacher_id = t.teacher_id "
                "ORDER BY c.course_no"
            )
            return cur.fetchall()


def teacher_options() -> list[dict]:
    """教师下拉选项（课程表单选授课教师用）"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT teacher_id, teacher_no, name FROM teachers ORDER BY teacher_no")
            return cur.fetchall()


# ---------------------------------------------------------------
# 成绩
# ---------------------------------------------------------------

def list_grades(student_id: int | None = None, course_id: int | None = None,
                page: int = 1, size: int = 10) -> dict:
    page = max(1, page)
    size = min(max(1, size), 100)
    where, params = [], []
    if student_id:
        where.append("g.student_id = %s")
        params.append(student_id)
    if course_id:
        where.append("g.course_id = %s")
        params.append(course_id)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    # 注意：列表里必须展示考试日期——唯一键已放宽为 (student, course, exam_date)，
    # 同一学生同一课程可能出现多条记录（重修/补考），日期列用于区分
    base = (
        "SELECT g.grade_id, g.student_id, g.course_id, g.score, g.exam_date, "
        "s.student_no, s.name AS student_name, s.class_name, "
        "c.course_no, c.course_name "
        "FROM grades g "
        "JOIN students s ON g.student_id = s.student_id "
        "JOIN courses c ON g.course_id = c.course_id "
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS total FROM grades g {where_sql}", params)
            total = cur.fetchone()["total"]
            cur.execute(
                f"{base} {where_sql} ORDER BY g.grade_id DESC LIMIT %s OFFSET %s",
                params + [size, (page - 1) * size],
            )
            items = cur.fetchall()
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": max(1, math.ceil(total / size)) if total else 1,
    }


def create_grade(data: dict) -> int:
    """插入成绩。

    双重校验：
    - 第一层（应用层）：schemas.GradeIn 的 pydantic 校验（score 0-100 等）
    - 第二层（数据库层）：trg_grades_check_insert 触发器 + CHECK 约束兜底，
      即使绕过应用直连数据库，非法数据也进不来
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO grades (student_id, course_id, score, exam_date) "
                "VALUES (%s, %s, %s, %s)",
                (data["student_id"], data["course_id"], data["score"], data["exam_date"]),
            )
            return cur.lastrowid


def update_grade(grade_id: int, data: dict) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE grades SET score = %s, exam_date = %s WHERE grade_id = %s",
                (data["score"], data["exam_date"], grade_id),
            )
            return cur.rowcount > 0


def delete_grade(grade_id: int) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM grades WHERE grade_id = %s", (grade_id,))
            return cur.rowcount > 0
