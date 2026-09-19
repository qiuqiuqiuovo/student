-- ============================================
-- 学生成绩数据库 - 高级对象脚本（视图 / 触发器 / 存储过程）
-- 数据库: MySQL 8.0+
-- 本脚本可重复执行（CREATE OR REPLACE VIEW / DROP TRIGGER IF EXISTS / DROP PROCEDURE IF EXISTS）
-- ============================================

USE score_db;

-- ============================================
-- 一、视图
-- ============================================

-- 视图1：学生综合成绩概览
-- 每名学生的课程门数 / 平均分 / 最高最低分 / 及格与不及格门数
-- 与 03_queries.sql 的查询7 口径一致，供 Web 端统计页与学生综合明细表格直接读取
CREATE OR REPLACE VIEW v_student_overview AS
SELECT
    s.student_id,
    s.student_no,
    s.name,
    s.class_name,
    s.major,
    COUNT(g.grade_id)                              AS course_count,
    ROUND(AVG(g.score), 2)                         AS avg_score,
    MAX(g.score)                                   AS max_score,
    MIN(g.score)                                   AS min_score,
    SUM(CASE WHEN g.score >= 60 THEN 1 ELSE 0 END) AS pass_count,
    SUM(CASE WHEN g.score <  60 THEN 1 ELSE 0 END) AS fail_count
FROM students s
LEFT JOIN grades g ON s.student_id = g.student_id
GROUP BY s.student_id, s.student_no, s.name, s.class_name, s.major;

-- 视图2：课程统计
-- 各课程的选修人数 / 平均分 / 最高最低分 / 及格率（含授课教师）
CREATE OR REPLACE VIEW v_course_stats AS
SELECT
    c.course_id,
    c.course_no,
    c.course_name,
    t.name                                          AS teacher_name,
    COUNT(g.grade_id)                               AS student_count,
    ROUND(AVG(g.score), 2)                          AS avg_score,
    MAX(g.score)                                    AS max_score,
    MIN(g.score)                                    AS min_score,
    ROUND(SUM(CASE WHEN g.score >= 60 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pass_rate
FROM courses c
LEFT JOIN grades g   ON c.course_id  = g.course_id
LEFT JOIN teachers t ON c.teacher_id = t.teacher_id
GROUP BY c.course_id, c.course_no, c.course_name, t.name;

-- ============================================
-- 二、触发器：成绩双重校验的"数据库层"
-- 与 grades 表的 CHECK 约束互补：
--   CHECK 约束    —— 保证基础分数范围（MySQL 8.0.16+ 强制执行）
--   BEFORE 触发器 —— 用 SIGNAL 输出中文业务报错，并校验"考试日期不能晚于今天"
-- 即使绕过应用程序直接操作数据库，非法成绩也无法入库（见 05 脚本演示二）
-- ============================================

DROP TRIGGER IF EXISTS trg_grades_check_insert;
DELIMITER $$
CREATE TRIGGER trg_grades_check_insert
BEFORE INSERT ON grades
FOR EACH ROW
BEGIN
    IF NEW.score < 0 OR NEW.score > 100 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '成绩必须在 0-100 之间';
    END IF;
    IF NEW.exam_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '考试日期不能晚于今天';
    END IF;
END$$
DELIMITER ;

-- MySQL 中一个 CREATE TRIGGER 只能绑定一个事件，UPDATE 需单独建一个触发器
DROP TRIGGER IF EXISTS trg_grades_check_update;
DELIMITER $$
CREATE TRIGGER trg_grades_check_update
BEFORE UPDATE ON grades
FOR EACH ROW
BEGIN
    IF NEW.score < 0 OR NEW.score > 100 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '成绩必须在 0-100 之间';
    END IF;
    IF NEW.exam_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '考试日期不能晚于今天';
    END IF;
END$$
DELIMITER ;

-- ============================================
-- 三、存储过程：按学号/课程号录入成绩（Web 端批量导入调用）
-- 设计要点：
--   1. 仅 IN 参数：便于 pymysql 直接 cursor.execute("CALL ...") 调用
--   2. 学号/课程号不存在时 SIGNAL 中文报错，应用层捕获后原样展示给用户
--   3. 同一学生+课程+日期已有成绩时更新分数（重修/补考按新考试日期另存一条）
--   4. ON DUPLICATE KEY UPDATE 使用 8.0.19+ 行别名语法 AS new（VALUES() 已弃用）
-- ============================================

DROP PROCEDURE IF EXISTS sp_insert_grade;
DELIMITER $$
CREATE PROCEDURE sp_insert_grade(
    IN p_student_no VARCHAR(20),
    IN p_course_no  VARCHAR(20),
    IN p_score      DECIMAL(5,2),
    IN p_exam_date  DATE
)
BEGIN
    DECLARE v_sid INT;
    DECLARE v_cid INT;

    SELECT student_id INTO v_sid FROM students WHERE student_no = p_student_no;
    IF v_sid IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '学号不存在';
    END IF;

    SELECT course_id INTO v_cid FROM courses WHERE course_no = p_course_no;
    IF v_cid IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '课程编号不存在';
    END IF;

    INSERT INTO grades (student_id, course_id, score, exam_date)
    VALUES (v_sid, v_cid, p_score, p_exam_date) AS new
    ON DUPLICATE KEY UPDATE score = new.score;
END$$
DELIMITER ;
