-- ============================================
-- 学生成绩数据库 - 事务演示脚本
-- 演示目的：事务原子性（Atomicity）——多条语句要么全部生效，要么全部回滚
--
-- 执行方式：本脚本演示二会故意触发触发器报错，
--           mysql 客户端默认遇到错误会中断脚本，因此需要加 --force 继续执行：
--     mysql --login-path=score_db --default-character-set=utf8mb4 --force < 05_transaction_demo.sql
--
-- 副作用说明：本脚本运行后会新增 3 条演示成绩（演示一 2 条 + 演示三 1 条），
--             如需还原数据请重跑 01 + 02 脚本
-- ============================================

USE score_db;

SELECT COUNT(*) AS 演示前成绩条数 FROM grades;

-- ============================================
-- 演示一：批量录入成功，整体提交
-- 为学号 20230101（刘思源）录入 2 门新课成绩：CS103 操作系统、MA202 概率论
-- ============================================
START TRANSACTION;
    CALL sp_insert_grade('20230101', 'CS103', 81.5, '2024-06-20');
    CALL sp_insert_grade('20230101', 'MA202', 90.0, '2024-06-22');
    -- 提交前自查：本事务内未提交的数据对当前会话可见
    SELECT s.name, c.course_name, g.score
    FROM grades g
    JOIN students s ON g.student_id = s.student_id
    JOIN courses c  ON g.course_id  = c.course_id
    WHERE s.student_no = '20230101' AND g.exam_date >= '2024-06-01';
COMMIT;

-- 提交后成绩总数应 = 演示前 + 2
SELECT COUNT(*) AS 演示一提交后成绩条数 FROM grades;

-- ============================================
-- 演示二：其中一条非法（150 分），整体回滚
-- 关键点：触发器 SIGNAL 只会让"当前这条语句"失败，事务本身仍然打开，
--         必须显式 ROLLBACK，已插入的合法行才会一并撤销
-- ============================================
START TRANSACTION;
    CALL sp_insert_grade('20230102', 'CS103', 75.0, '2024-06-20');   -- 合法
    CALL sp_insert_grade('20230102', 'MA202', 150.0, '2024-06-22');  -- 非法：触发器拦截，报"成绩必须在 0-100 之间"
ROLLBACK;

-- 回滚后成绩总数应与演示一提交后相同（非法批次的合法行也没留下）
SELECT COUNT(*) AS 演示二回滚后成绩条数 FROM grades;

-- ============================================
-- 演示三：SAVEPOINT 部分回滚
-- 保留第一条成绩，只撤销第二条（模拟"其中一行填错，只撤回这一行"）
-- ============================================
START TRANSACTION;
    CALL sp_insert_grade('20230103', 'CS103', 88.0, '2024-06-20');
    SAVEPOINT sp1;
    CALL sp_insert_grade('20230103', 'MA202', 66.0, '2024-06-22');
    ROLLBACK TO SAVEPOINT sp1;   -- 撤销第二条，第一条保留
COMMIT;

-- 验证：20230103 只剩 CS103 一条新成绩（MA202 已被部分回滚撤销）
SELECT s.name, c.course_name, g.score
FROM grades g
JOIN students s ON g.student_id = s.student_id
JOIN courses c  ON g.course_id  = c.course_id
WHERE s.student_no = '20230103' AND g.exam_date >= '2024-06-01';

SELECT COUNT(*) AS 演示全部结束后成绩条数 FROM grades;
