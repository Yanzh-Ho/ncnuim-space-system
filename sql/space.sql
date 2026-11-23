
CREATE TABLE IF NOT EXISTS spaces (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    capacity INTEGER NOT NULL,
    description TEXT
);

INSERT INTO spaces (name, location, capacity, description)
VALUES
('管理學院 101 教室', '管理學院 1 樓', 50, '一般教學教室'),
('管理學院 102 教室', '管理學院 1 樓', 40, '一般教學教室'),
('管理學院 201 教室', '管理學院 2 樓', 60, '大型教室'),
('會議室 A', '管理學院 3 樓', 20, '小型會議室');
