DROP TABLE IF EXISTS rooms CASCADE;

CREATE TABLE rooms (
    id           SERIAL PRIMARY KEY,
    room_code    VARCHAR(20) UNIQUE NOT NULL,   -- 教室編號 (如 201, 202, 305)
    room_name    VARCHAR(100) NOT NULL,         -- 教室名稱 (如 管院電腦教室A)
    floor        VARCHAR(10) NOT NULL,          -- 樓層 (如 1F, 2F, 3F, 4F)
    capacity     INT NOT NULL DEFAULT 0,        -- 容納人數
    equipment    TEXT DEFAULT '',               -- 設備說明
    description  TEXT DEFAULT '',               -- 詳細介紹與使用規範
    pano_url     VARCHAR(255) DEFAULT '',       -- 360全景圖片路徑
    map_x        FLOAT NOT NULL DEFAULT 50.0,   -- 平面圖 X 座標 (%)
    map_y        FLOAT NOT NULL DEFAULT 50.0    -- 平面圖 Y 座標 (%)
);

-- 預設塞入幾間管院教室資料 (之後管理員也能從網頁新增修改)
INSERT INTO rooms (room_code, room_name, floor, capacity, equipment, description, pano_url, map_x, map_y) VALUES
('201', '管院大型階梯教室', '2F', 120, '雙單槍投影機、無線麥克風、講桌電腦、冷氣', '適合專題演講、大型必修課程與系學會活動。', 'https://pannellum.org/images/alma.jpg', 32.5, 45.0),
('202', '資管專業電腦教室(一)', '2F', 65, '桌上型電腦 65 台、廣播教學系統、單槍投影機', '配備完整程式開發與資料庫軟體，供上機實作課程使用。', 'https://pannellum.org/images/bma-1.jpg', 68.0, 45.0),
('305', '個案研討室', '3F', 40, '移動式分組桌椅、75吋觸控大螢幕、白板牆', '適合小組討論、專案發表與個案分析課程。', 'https://pannellum.org/images/cerro-toco-0.jpg', 48.0, 62.0);