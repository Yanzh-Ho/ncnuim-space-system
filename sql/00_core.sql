DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id        varchar(20) PRIMARY KEY,               
    pwd       varchar(50) NOT NULL,                  
    name      varchar(30) NOT NULL,                  
    role      varchar(10) NOT NULL
              CHECK (role IN ('admin', 'teacher', 'student')),   
    approved  boolean NOT NULL DEFAULT false         
);

INSERT INTO users (id, pwd, name, role, approved) VALUES
('admin',    '123', '系統管理員', 'admin',   true),
('teacher1', '123', '王老師',     'teacher', true),
('teacher2', '123', '李老師',     'teacher', true),
('student1', '123', '陳同學',     'student', true),
('newuser',  '123', '新同學',     'student', false);
