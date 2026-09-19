-- ============================================
-- 学生成绩数据库 - 建表脚本
-- 数据库: MySQL 8.0+（CHECK 约束需 8.0.16+ 才强制执行，窗口函数需 8.0+）
-- ============================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS score_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE score_db;

-- 删除已存在的表（按依赖顺序倒序删除）
DROP TABLE IF EXISTS grades;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS teachers;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS users;

-- ============================================
-- 1. 学生表 (students)
-- 注：建表必须显式写 COLLATE=utf8mb4_unicode_ci，与建库保持一致。
--     只写 CHARSET=utf8mb4 时 MySQL 会改用字符集默认排序规则（8.0 为
--     utf8mb4_0900_ai_ci），与库/存储过程参数的 unicode_ci 比较字符串
--     会报 ERROR 1267（Illegal mix of collations）。
-- ============================================
CREATE TABLE students (
    student_id    INT           NOT NULL AUTO_INCREMENT  COMMENT '学生ID，主键',
    student_no    VARCHAR(20)   NOT NULL UNIQUE           COMMENT '学号，唯一',
    name          VARCHAR(50)   NOT NULL                  COMMENT '姓名',
    gender        ENUM('男','女') NOT NULL DEFAULT '男'     COMMENT '性别',
    birth_date    DATE                    DEFAULT NULL    COMMENT '出生日期',
    major         VARCHAR(50)             DEFAULT NULL    COMMENT '专业',
    class_name    VARCHAR(50)             DEFAULT NULL    COMMENT '班级',
    enrollment_date DATE                   DEFAULT NULL   COMMENT '入学日期',
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    PRIMARY KEY (student_id),
    KEY idx_major (major),      -- 按专业查询/分组（专业排名统计）
    KEY idx_class (class_name)  -- 按班级查询/分组（班级对比统计）
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生信息表';

-- ============================================
-- 2. 教师表 (teachers)
-- ============================================
CREATE TABLE teachers (
    teacher_id    INT           NOT NULL AUTO_INCREMENT  COMMENT '教师ID，主键',
    teacher_no    VARCHAR(20)   NOT NULL UNIQUE           COMMENT '工号，唯一',
    name          VARCHAR(50)   NOT NULL                  COMMENT '姓名',
    gender        ENUM('男','女') NOT NULL DEFAULT '男'     COMMENT '性别',
    title         VARCHAR(30)             DEFAULT NULL    COMMENT '职称',
    department    VARCHAR(50)             DEFAULT NULL    COMMENT '所属院系',
    phone         VARCHAR(20)             DEFAULT NULL    COMMENT '联系电话',
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    PRIMARY KEY (teacher_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='教师信息表';

-- ============================================
-- 3. 课程表 (courses)
-- ============================================
CREATE TABLE courses (
    course_id     INT           NOT NULL AUTO_INCREMENT  COMMENT '课程ID，主键',
    course_no     VARCHAR(20)   NOT NULL UNIQUE           COMMENT '课程编号，唯一',
    course_name   VARCHAR(100)  NOT NULL                  COMMENT '课程名称',
    credits       DECIMAL(3,1)  NOT NULL DEFAULT 2.0      COMMENT '学分',
    teacher_id    INT                     DEFAULT NULL    COMMENT '授课教师ID，外键',
    semester      VARCHAR(20)             DEFAULT NULL    COMMENT '开课学期',
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    PRIMARY KEY (course_id),
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程信息表';

-- ============================================
-- 4. 成绩表 (grades)
-- ============================================
CREATE TABLE grades (
    grade_id      INT           NOT NULL AUTO_INCREMENT  COMMENT '成绩记录ID，主键',
    student_id    INT           NOT NULL                  COMMENT '学生ID，外键',
    course_id     INT           NOT NULL                  COMMENT '课程ID，外键',
    score         DECIMAL(5,2)            DEFAULT NULL    COMMENT '成绩（0-100分）',
    exam_date     DATE          NOT NULL                  COMMENT '考试日期',
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    PRIMARY KEY (grade_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    -- 同一学生同一课程同一考试日期唯一：允许重修/补考（按不同考试日期各留一条记录）
    UNIQUE KEY uk_student_course_exam (student_id, course_id, exam_date),
    KEY idx_exam_date (exam_date),  -- 按考试日期筛选（补考查询/学期成绩）
    CHECK (score >= 0 AND score <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生成绩表';

-- ============================================
-- 5. 系统用户表 (users)
-- ============================================
CREATE TABLE users (
    user_id       INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '用户ID，主键',
    username      VARCHAR(32)   NOT NULL                 COMMENT '登录名',
    password_hash VARCHAR(255)  NOT NULL                 COMMENT 'PBKDF2-SHA256 密码哈希（格式: pbkdf2_sha256$迭代次数$盐hex$哈希hex）',
    nickname      VARCHAR(32)             DEFAULT NULL   COMMENT '昵称',
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';
