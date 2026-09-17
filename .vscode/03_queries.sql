-- ============================================
-- 学生成绩数据库 - 统计查询脚本
-- ============================================

USE score_db;

-- ============================================
-- 查询1：查询指定学生的所有课程成绩
-- ============================================
-- 示例：查询学号 20230102（黄子涵）的全部成绩
SELECT
    s.student_no           AS 学号,
    s.name                 AS 姓名,
    s.class_name           AS 班级,
    c.course_no            AS 课程编号,
    c.course_name           AS 课程名称,
    g.score                AS 成绩,
    g.exam_date            AS 考试日期
FROM grades g
JOIN students s ON g.student_id = s.student_id
JOIN courses c  ON g.course_id  = c.course_id
WHERE s.student_no = '20230102'
ORDER BY g.exam_date;


-- ============================================
-- 查询2：查询指定课程的所有学生成绩及排名
-- ============================================
-- 示例：查询「数据结构」(CS101) 全部学生成绩，按成绩降序排列
SELECT
    c.course_name           AS 课程名称,
    s.student_no            AS 学号,
    s.name                  AS 姓名,
    s.class_name            AS 班级,
    g.score                 AS 成绩,
    RANK() OVER (ORDER BY g.score DESC) AS 排名
FROM grades g
JOIN students s ON g.student_id = s.student_id
JOIN courses c  ON g.course_id  = c.course_id
WHERE c.course_no = 'CS101'
ORDER BY g.score DESC;


-- ============================================
-- 查询3：统计各课程的平均分、最高分、最低分、及格率
-- ============================================
SELECT
    c.course_no             AS 课程编号,
    c.course_name           AS 课程名称,
    t.name                  AS 授课教师,
    COUNT(g.grade_id)       AS 选修人数,
    ROUND(AVG(g.score), 2)  AS 平均分,
    MAX(g.score)            AS 最高分,
    MIN(g.score)            AS 最低分,
    CONCAT(ROUND(SUM(CASE WHEN g.score >= 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1), '%') AS 及格率
FROM courses c
JOIN grades g   ON c.course_id  = g.course_id
LEFT JOIN teachers t ON c.teacher_id = t.teacher_id
GROUP BY c.course_id, c.course_no, c.course_name, t.name
ORDER BY 平均分 DESC;


-- ============================================
-- 查询4：统计各班级各科平均分对比
-- ============================================
SELECT
    s.class_name            AS 班级,
    c.course_name           AS 课程名称,
    COUNT(*)                AS 考试人数,
    ROUND(AVG(g.score), 2)  AS 平均分,
    ROUND(MAX(g.score), 2)  AS 最高分,
    ROUND(MIN(g.score), 2)  AS 最低分
FROM grades g
JOIN students s ON g.student_id = s.student_id
JOIN courses c  ON g.course_id  = c.course_id
GROUP BY s.class_name, c.course_name
ORDER BY s.class_name, c.course_name;


-- ============================================
-- 查询5：查询不及格成绩（成绩 < 60）的学生及课程
-- ============================================
SELECT
    s.student_no            AS 学号,
    s.name                  AS 姓名,
    s.class_name            AS 班级,
    c.course_name           AS 课程名称,
    g.score                 AS 成绩
FROM grades g
JOIN students s ON g.student_id = s.student_id
JOIN courses c  ON g.course_id  = c.course_id
WHERE g.score < 60
ORDER BY g.score ASC;


-- ============================================
-- 查询6：查询各专业平均成绩排名
-- ============================================
SELECT
    s.major                 AS 专业,
    COUNT(DISTINCT s.student_id) AS 学生人数,
    ROUND(AVG(g.score), 2)  AS 专业平均分,
    MAX(g.score)            AS 最高分
FROM grades g
JOIN students s ON g.student_id = s.student_id
GROUP BY s.major
ORDER BY 专业平均分 DESC;


-- ============================================
-- 查询7：查询每名学生各科成绩及平均分（综合视图）
-- ============================================
SELECT
    s.student_no            AS 学号,
    s.name                  AS 姓名,
    s.class_name            AS 班级,
    COUNT(g.grade_id)       AS 课程门数,
    ROUND(AVG(g.score), 2)  AS 平均分,
    MAX(g.score)            AS 最高单科成绩,
    MIN(g.score)            AS 最低单科成绩,
    SUM(CASE WHEN g.score >= 60 THEN 1 ELSE 0 END) AS 及格门数,
    SUM(CASE WHEN g.score < 60 THEN 1 ELSE 0 END)  AS 不及格门数
FROM students s
LEFT JOIN grades g ON s.student_id = g.student_id
GROUP BY s.student_id, s.student_no, s.name, s.class_name
ORDER BY 平均分 DESC;


-- ============================================
-- 查询8：成绩分段统计（90+、80-89、70-79、60-69、<60）
-- ============================================
SELECT
    c.course_name           AS 课程名称,
    SUM(CASE WHEN g.score >= 90 THEN 1 ELSE 0 END) AS '90分以上',
    SUM(CASE WHEN g.score >= 80 AND g.score < 90 THEN 1 ELSE 0 END) AS '80-89分',
    SUM(CASE WHEN g.score >= 70 AND g.score < 80 THEN 1 ELSE 0 END) AS '70-79分',
    SUM(CASE WHEN g.score >= 60 AND g.score < 70 THEN 1 ELSE 0 END) AS '60-69分',
    SUM(CASE WHEN g.score < 60 THEN 1 ELSE 0 END) AS '不及格'
FROM grades g
JOIN courses c ON g.course_id = c.course_id
GROUP BY c.course_name
ORDER BY c.course_name;
