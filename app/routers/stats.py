"""统计报表：仪表盘首页 + /stats 页面 + /api/stats/* 图表数据接口。

统计口径与 sql/03_queries.sql 保持一致，部分查询直接读取 04 脚本创建的视图
（v_student_overview / v_course_stats），体现"视图封装复杂统计"的设计。
"""
from fastapi import APIRouter, Depends, Request

from app import db
from app.deps import require_user_api, require_user_page
from app.templating import templates

router = APIRouter()


def _query(sql: str, params: tuple = ()) -> list[dict]:
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def _query_one(sql: str, params: tuple = ()) -> dict:
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() or {}


# ---------------------------------------------------------------
# 页面
# ---------------------------------------------------------------

@router.get("/")
def dashboard_page(request: Request, user=Depends(require_user_page)):
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "overview": get_overview(),
        "score_distribution": get_score_distribution(),
        "gender_dist": get_gender_dist(),
    })


@router.get("/stats")
def stats_page(request: Request, user=Depends(require_user_page)):
    return templates.TemplateResponse(request, "stats.html", {
        "user": user,
        "overview": get_overview(),
    })


# ---------------------------------------------------------------
# 图表数据接口
# ---------------------------------------------------------------

def get_overview() -> dict:
    """KPI 总览：各表记录数 + 全库平均分 + 及格率"""
    return _query_one(
        """
        SELECT
            (SELECT COUNT(*) FROM students) AS student_count,
            (SELECT COUNT(*) FROM teachers) AS teacher_count,
            (SELECT COUNT(*) FROM courses)  AS course_count,
            (SELECT COUNT(*) FROM grades)   AS grade_count,
            (SELECT ROUND(AVG(score), 2) FROM grades WHERE score IS NOT NULL) AS overall_avg,
            (SELECT ROUND(SUM(CASE WHEN score >= 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
             FROM grades WHERE score IS NOT NULL) AS overall_pass_rate
        """
    )


@router.get("/api/stats/overview")
def api_overview(user=Depends(require_user_api)):
    return get_overview()


def get_score_distribution() -> list[dict]:
    """成绩分段分布（横向柱状图）"""
    return _query(
        """
        SELECT
            CASE WHEN score >= 90 THEN '90-100'
                 WHEN score >= 80 THEN '80-89'
                 WHEN score >= 70 THEN '70-79'
                 WHEN score >= 60 THEN '60-69'
                 ELSE '59及以下' END AS seg,
            COUNT(*) AS cnt
        FROM grades
        GROUP BY seg
        ORDER BY FIELD(seg, '90-100', '80-89', '70-79', '60-69', '59及以下')
        """
    )


@router.get("/api/stats/score_distribution")
def api_score_distribution(user=Depends(require_user_api)):
    return get_score_distribution()


@router.get("/api/stats/course_avg")
def api_course_avg(user=Depends(require_user_api)):
    """各课程平均分（纵向柱状图）"""
    return _query(
        """
        SELECT c.course_name AS name, ROUND(AVG(g.score), 1) AS avg_score
        FROM grades g JOIN courses c ON g.course_id = c.course_id
        GROUP BY c.course_id, c.course_name
        ORDER BY avg_score DESC
        """
    )


@router.get("/api/stats/course_pass_rate")
def api_course_pass_rate(user=Depends(require_user_api)):
    """各课程及格率（横向柱状图，0-100 单轴 + 60% 及格线）"""
    return _query(
        """
        SELECT c.course_name AS name,
               ROUND(SUM(CASE WHEN g.score >= 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                   AS pass_rate
        FROM grades g JOIN courses c ON g.course_id = c.course_id
        GROUP BY c.course_id, c.course_name
        ORDER BY pass_rate DESC
        """
    )


@router.get("/api/stats/class_course_avg")
def api_class_course_avg(user=Depends(require_user_api)):
    """班级 × 课程平均分（分组柱状图，前端做行转列 pivot）"""
    return _query(
        """
        SELECT s.class_name, c.course_name, ROUND(AVG(g.score), 2) AS v
        FROM grades g
        JOIN students s ON g.student_id = s.student_id
        JOIN courses c  ON g.course_id  = c.course_id
        GROUP BY s.class_name, c.course_name
        ORDER BY s.class_name, c.course_name
        """
    )


@router.get("/api/stats/major_avg")
def api_major_avg(user=Depends(require_user_api)):
    """各专业平均分（横向柱状图）"""
    return _query(
        """
        SELECT s.major AS name, ROUND(AVG(g.score), 1) AS avg_score
        FROM grades g JOIN students s ON g.student_id = s.student_id
        GROUP BY s.major
        ORDER BY avg_score DESC
        """
    )


def get_gender_dist() -> list[dict]:
    """性别分布（2 个类别不做饼图，以 stat tile 数字卡呈现）"""
    return _query("SELECT gender AS name, COUNT(*) AS value FROM students GROUP BY gender")


@router.get("/api/stats/gender_dist")
def api_gender_dist(user=Depends(require_user_api)):
    return get_gender_dist()


@router.get("/api/stats/student_scatter")
def api_student_scatter(user=Depends(require_user_api)):
    """学生综合散点：x=课程门数，y=平均分，颜色=专业（读自 v_student_overview 视图）"""
    return _query(
        """
        SELECT name, course_count AS x, avg_score AS y, major, class_name, max_score
        FROM v_student_overview
        WHERE course_count > 0
        ORDER BY student_id
        """
    )


@router.get("/api/stats/course_top")
def api_course_top(user=Depends(require_user_api)):
    """各课程第一名（RANK() OVER 窗口函数，横向柱状图）"""
    return _query(
        """
        SELECT c.course_name AS course_name, s.name AS student_name,
               s.class_name, t.score
        FROM (
            SELECT student_id, course_id, score,
                   RANK() OVER (PARTITION BY course_id ORDER BY score DESC) AS rk
            FROM grades
        ) t
        JOIN students s ON t.student_id = s.student_id
        JOIN courses c  ON t.course_id  = c.course_id
        WHERE t.rk = 1
        ORDER BY c.course_id
        """
    )


@router.get("/api/stats/fail_list")
def api_fail_list(user=Depends(require_user_api)):
    """不及格名单（HTML 表格）"""
    return _query(
        """
        SELECT s.student_no, s.name, s.class_name, c.course_name, g.score
        FROM grades g
        JOIN students s ON g.student_id = s.student_id
        JOIN courses c  ON g.course_id  = c.course_id
        WHERE g.score < 60
        ORDER BY g.score
        """
    )


@router.get("/api/stats/student_table")
def api_student_table(user=Depends(require_user_api)):
    """学生综合明细（HTML 表格，读自 v_student_overview 视图）"""
    return _query("SELECT * FROM v_student_overview ORDER BY avg_score DESC")
