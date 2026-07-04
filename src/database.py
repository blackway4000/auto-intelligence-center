"""SQLite database for Auto Intelligence Center.

Schema:
- brands: brand basic info
- vehicles: vehicle basic info
- vehicle_specs: detailed specs (power, battery, dimensions, etc.)
- prices: price history
- content_sources: multi-channel content (official, MIIT, media)
- competitors: competitive relationship mapping
- crawled_data: raw crawl data
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import DB_PATH


# ============ Schema ============

_SCHEMA = '''
-- Brands
CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    name_en TEXT,
    website TEXT,
    logo_url TEXT,
    category TEXT,           -- 新能源 / 传统 / 豪华 / 新势力
    country TEXT,
    parent_brand TEXT,       -- 母公司，如比亚迪->腾势
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vehicles
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY,
    brand_id INTEGER,
    name TEXT NOT NULL,
    segment TEXT,            -- 紧凑型/中型/大型 SUV/轿车/MPV
    body_type TEXT,          -- SUV / 轿车 / MPV / 跑车
    power_type TEXT,         -- 纯电 / 插混 / 增程 / 燃油
    platform TEXT,           -- 平台架构
    status TEXT,             -- 申报 / 预售 / 上市 / 改款
    announce_date DATE,
    presale_date DATE,
    launch_date DATE,
    facelift_date DATE,
    length INTEGER,
    width INTEGER,
    height INTEGER,
    wheelbase INTEGER,
    image_urls TEXT,
    source_url TEXT,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vehicle Specs (detailed technical data)
CREATE TABLE IF NOT EXISTS vehicle_specs (
    id INTEGER PRIMARY KEY,
    vehicle_id INTEGER NOT NULL,
    motor_type TEXT,         -- 单电机/双电机/三电机
    motor_power TEXT,        -- e.g. "200kW" or "前150后200"
    motor_torque TEXT,
    battery_capacity REAL,   -- kWh
    battery_brand TEXT,      -- 宁德时代 / 比亚迪 / 中创新航
    battery_type TEXT,       -- 磷酸铁锂 / 三元锂 / 固态
    range_cltc INTEGER,      -- km
    range_wltc INTEGER,
    range_nedc INTEGER,
    charging_time REAL,      -- 小时 (快充30-80%)
    drivetrain TEXT,         -- 前驱 / 后驱 / 四驱
    suspension_front TEXT,
    suspension_rear TEXT,
    adas_level TEXT,         -- L2 / L2+ / L3
    chip TEXT,               -- 8295 / 图灵 / Orin-X
    radar TEXT,              -- 激光雷达数量
    camera_count INTEGER,
    brakes_front TEXT,
    brakes_rear TEXT,
    curb_weight INTEGER,     -- kg
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prices
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY,
    vehicle_id INTEGER,
    price_type TEXT,         -- 预售价 / 正式价 / 权益价
    min_price DECIMAL,
    max_price DECIMAL,
    currency TEXT DEFAULT 'CNY',
    effective_date DATE,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Multi-channel Content Sources
CREATE TABLE IF NOT EXISTS content_sources (
    id INTEGER PRIMARY KEY,
    vehicle_id INTEGER,
    source_type TEXT,        -- official / miit / media / social
    source_name TEXT,        -- 官网 / 工信部 / 汽车之家 / 懂车帝
    source_url TEXT,
    title TEXT,
    content_summary TEXT,
    publish_date DATE,
    images TEXT,             -- JSON array of image URLs
    status TEXT DEFAULT 'pending',  -- pending / processed / failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Competitors
CREATE TABLE IF NOT EXISTS competitors (
    id INTEGER PRIMARY KEY,
    vehicle_id INTEGER NOT NULL,
    competitor_vehicle_id INTEGER NOT NULL,
    relationship_type TEXT,  -- 同级 / 同价位 / 同动力 / 同品牌
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vehicle_id, competitor_vehicle_id)
);

-- Crawled Raw Data
CREATE TABLE IF NOT EXISTS crawled_data (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_url TEXT,
    raw_title TEXT,
    raw_content TEXT,
    publish_date DATE,
    status TEXT DEFAULT 'pending',
    extracted_vehicle_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_vehicles_brand ON vehicles(brand_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status);
CREATE INDEX IF NOT EXISTS idx_vehicles_launch ON vehicles(launch_date);
CREATE INDEX IF NOT EXISTS idx_prices_vehicle ON prices(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_content_vehicle ON content_sources(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_content_type ON content_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_competitors_vehicle ON competitors(vehicle_id);
'''


def init_db():
    """Initialize the database with required tables.
    
    Handles schema migrations by adding missing columns to existing tables.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create new tables if not exist
    cursor.executescript(_SCHEMA)
    
    # Migrate existing brands table: add missing columns
    cursor.execute("PRAGMA table_info(brands)")
    existing_brand_cols = {row[1] for row in cursor.fetchall()}
    new_brand_cols = {
        'logo_url': 'TEXT',
        'category': 'TEXT',
        'country': 'TEXT',
        'parent_brand': 'TEXT',
    }
    for col, col_type in new_brand_cols.items():
        if col not in existing_brand_cols:
            cursor.execute(f"ALTER TABLE brands ADD COLUMN {col} {col_type}")
    
    # Migrate existing vehicles table: add missing columns
    cursor.execute("PRAGMA table_info(vehicles)")
    existing_vehicle_cols = {row[1] for row in cursor.fetchall()}
    new_vehicle_cols = {
        'body_type': 'TEXT',
        'platform': 'TEXT',
        'length': 'INTEGER',
        'width': 'INTEGER',
        'height': 'INTEGER',
        'wheelbase': 'INTEGER',
    }
    for col, col_type in new_vehicle_cols.items():
        if col not in existing_vehicle_cols:
            cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col} {col_type}")
    
    conn.commit()
    conn.close()


def get_connection():
    return sqlite3.connect(DB_PATH)


# ============ Brand CRUD ============

def insert_brand(name: str, name_en: Optional[str] = None,
                 website: Optional[str] = None, **kwargs) -> int:
    """Insert a brand and return its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    fields = ['name']
    values = [name]
    
    for key in ['name_en', 'website', 'logo_url', 'category', 'country', 'parent_brand']:
        if key in kwargs:
            fields.append(key)
            values.append(kwargs[key])
    
    placeholders = ', '.join(['?'] * len(fields))
    sql = f"INSERT INTO brands ({', '.join(fields)}) VALUES ({placeholders})"
    
    cursor.execute(sql, values)
    conn.commit()
    brand_id = cursor.lastrowid
    conn.close()
    return brand_id


def get_or_create_brand(name: str, name_en: Optional[str] = None,
                        website: Optional[str] = None, **kwargs) -> int:
    """Get brand ID or create if not exists."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM brands WHERE name = ?", (name,))
    row = cursor.fetchone()
    
    if row:
        brand_id = row[0]
    else:
        fields = ['name', 'name_en', 'website']
        values = [name, name_en, website]
        
        for key in ['logo_url', 'category', 'country', 'parent_brand']:
            if key in kwargs:
                fields.append(key)
                values.append(kwargs[key])
        
        placeholders = ', '.join(['?'] * len(fields))
        sql = f"INSERT INTO brands ({', '.join(fields)}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        conn.commit()
        brand_id = cursor.lastrowid
    
    conn.close()
    return brand_id


def list_brands(category: Optional[str] = None) -> List[Dict]:
    """List all brands, optionally filtered by category."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if category:
        cursor.execute("SELECT * FROM brands WHERE category = ? ORDER BY name", (category,))
    else:
        cursor.execute("SELECT * FROM brands ORDER BY name")
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============ Vehicle CRUD ============

def insert_vehicle(brand_id: int, name: str, **kwargs) -> int:
    """Insert a new vehicle and return its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    fields = ['brand_id', 'name']
    values = [brand_id, name]
    
    for key in ['segment', 'body_type', 'power_type', 'platform', 'status',
                'announce_date', 'presale_date', 'launch_date', 'facelift_date',
                'length', 'width', 'height', 'wheelbase',
                'image_urls', 'source_url', 'tags']:
        if key in kwargs:
            fields.append(key)
            values.append(kwargs[key])
    
    placeholders = ', '.join(['?'] * len(fields))
    sql = f"INSERT INTO vehicles ({', '.join(fields)}) VALUES ({placeholders})"
    
    cursor.execute(sql, values)
    conn.commit()
    vehicle_id = cursor.lastrowid
    conn.close()
    return vehicle_id


def get_vehicle_by_name(name: str) -> Optional[Dict]:
    """Find vehicle by name."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM vehicles WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def update_vehicle(vehicle_id: int, **kwargs) -> None:
    """Update vehicle fields."""
    conn = get_connection()
    cursor = conn.cursor()
    
    allowed = ['segment', 'body_type', 'power_type', 'platform', 'status',
               'announce_date', 'presale_date', 'launch_date', 'facelift_date',
               'length', 'width', 'height', 'wheelbase',
               'image_urls', 'source_url', 'tags']
    
    updates = []
    values = []
    for key, value in kwargs.items():
        if key in allowed:
            updates.append(f"{key} = ?")
            values.append(value)
    
    if not updates:
        return
    
    values.append(vehicle_id)
    sql = f"UPDATE vehicles SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
    
    cursor.execute(sql, values)
    conn.commit()
    conn.close()


def list_vehicles(status: Optional[str] = None, brand_id: Optional[int] = None) -> List[Dict]:
    """List all vehicles with optional filters."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    if brand_id:
        conditions.append("brand_id = ?")
        params.append(brand_id)
    
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
        cursor.execute(f"SELECT * FROM vehicles {where_clause} ORDER BY updated_at DESC", params)
    else:
        cursor.execute("SELECT * FROM vehicles ORDER BY updated_at DESC")
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============ Vehicle Specs CRUD ============

def insert_specs(vehicle_id: int, **kwargs) -> int:
    """Insert vehicle specs."""
    conn = get_connection()
    cursor = conn.cursor()
    
    fields = ['vehicle_id']
    values = [vehicle_id]
    
    for key in ['motor_type', 'motor_power', 'motor_torque',
                'battery_capacity', 'battery_brand', 'battery_type',
                'range_cltc', 'range_wltc', 'range_nedc',
                'charging_time', 'drivetrain',
                'suspension_front', 'suspension_rear',
                'adas_level', 'chip', 'radar', 'camera_count',
                'brakes_front', 'brakes_rear', 'curb_weight']:
        if key in kwargs:
            fields.append(key)
            values.append(kwargs[key])
    
    placeholders = ', '.join(['?'] * len(fields))
    sql = f"INSERT INTO vehicle_specs ({', '.join(fields)}) VALUES ({placeholders})"
    
    cursor.execute(sql, values)
    conn.commit()
    spec_id = cursor.lastrowid
    conn.close()
    return spec_id


def get_specs(vehicle_id: int) -> Optional[Dict]:
    """Get specs for a vehicle."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM vehicle_specs WHERE vehicle_id = ?", (vehicle_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


# ============ Price CRUD ============

def insert_price(vehicle_id: int, price_type: str, min_price: float,
                 max_price: Optional[float] = None, **kwargs) -> int:
    """Insert a price record."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO prices (vehicle_id, price_type, min_price, max_price, currency, effective_date, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (vehicle_id, price_type, min_price, max_price or min_price,
          kwargs.get('currency', 'CNY'), kwargs.get('effective_date'), kwargs.get('source_url')))
    
    conn.commit()
    price_id = cursor.lastrowid
    conn.close()
    return price_id


def get_latest_price(vehicle_id: int) -> Optional[Dict]:
    """Get latest price for a vehicle."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM prices 
        WHERE vehicle_id = ? 
        ORDER BY effective_date DESC, created_at DESC 
        LIMIT 1
    """, (vehicle_id,))
    
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_price_history(vehicle_id: int) -> List[Dict]:
    """Get full price history for a vehicle."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM prices 
        WHERE vehicle_id = ? 
        ORDER BY effective_date DESC, created_at DESC
    """, (vehicle_id,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============ Content Sources CRUD ============

def insert_content_source(vehicle_id: Optional[int], source_type: str,
                          source_name: str, source_url: str,
                          title: str, **kwargs) -> int:
    """Insert a content source record."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO content_sources 
        (vehicle_id, source_type, source_name, source_url, title, content_summary, publish_date, images)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (vehicle_id, source_type, source_name, source_url, title,
          kwargs.get('content_summary'), kwargs.get('publish_date'),
          json.dumps(kwargs.get('images', [])) if kwargs.get('images') else None))
    
    conn.commit()
    content_id = cursor.lastrowid
    conn.close()
    return content_id


def list_content_sources(vehicle_id: Optional[int] = None,
                         source_type: Optional[str] = None) -> List[Dict]:
    """List content sources with optional filters."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if vehicle_id:
        conditions.append("vehicle_id = ?")
        params.append(vehicle_id)
    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type)
    
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)
        cursor.execute(f"SELECT * FROM content_sources {where_clause} ORDER BY publish_date DESC", params)
    else:
        cursor.execute("SELECT * FROM content_sources ORDER BY publish_date DESC")
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============ Competitors CRUD ============

def add_competitor(vehicle_id: int, competitor_vehicle_id: int,
                   relationship_type: str, notes: Optional[str] = None) -> bool:
    """Add a competitor relationship."""
    if vehicle_id == competitor_vehicle_id:
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO competitors (vehicle_id, competitor_vehicle_id, relationship_type, notes)
            VALUES (?, ?, ?, ?)
        ''', (vehicle_id, competitor_vehicle_id, relationship_type, notes))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_competitors(vehicle_id: int) -> List[Dict]:
    """Get all competitors for a vehicle."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT c.*, v.name as competitor_name, v.segment, v.power_type
        FROM competitors c
        JOIN vehicles v ON c.competitor_vehicle_id = v.id
        WHERE c.vehicle_id = ?
    """, (vehicle_id,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def find_potential_competitors(vehicle_id: int) -> List[Dict]:
    """Find potential competitors based on segment and price range."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get target vehicle info
    cursor.execute("SELECT segment, power_type FROM vehicles WHERE id = ?", (vehicle_id,))
    vehicle = cursor.fetchone()
    
    if not vehicle:
        conn.close()
        return []
    
    # Find same segment, exclude self and existing competitors
    cursor.execute("""
        SELECT v.*, b.name as brand_name,
               (SELECT min_price FROM prices WHERE vehicle_id = v.id ORDER BY effective_date DESC LIMIT 1) as latest_price
        FROM vehicles v
        JOIN brands b ON v.brand_id = b.id
        WHERE v.segment = ?
          AND v.id != ?
          AND v.id NOT IN (
              SELECT competitor_vehicle_id FROM competitors WHERE vehicle_id = ?
          )
        ORDER BY v.updated_at DESC
        LIMIT 20
    """, (vehicle['segment'], vehicle_id, vehicle_id))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============ Crawled Data CRUD ============

def insert_crawled(source: str, source_url: str, raw_title: str,
                   raw_content: Optional[str] = None, publish_date: Optional[str] = None) -> int:
    """Insert crawled raw data."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO crawled_data (source, source_url, raw_title, raw_content, publish_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (source, source_url, raw_title, raw_content, publish_date))
    
    conn.commit()
    data_id = cursor.lastrowid
    conn.close()
    return data_id


def get_pending_crawled(limit: int = 100) -> List[Dict]:
    """Get pending items for processing."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM crawled_data 
        WHERE status = 'pending' 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_crawled_processed(data_id: int, vehicle_id: Optional[int] = None) -> None:
    """Mark crawled item as processed."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE crawled_data 
        SET status = 'processed', extracted_vehicle_id = ? 
        WHERE id = ?
    ''', (vehicle_id, data_id))
    
    conn.commit()
    conn.close()


# ============ Initialization ============

def init_brands():
    """Initialize default brands with categories."""
    brands = [
        ('小米汽车', 'Xiaomi Auto', 'https://www.xiaomiev.com', '新势力', '中国', None),
        ('比亚迪', 'BYD', 'https://www.byd.com', '新能源', '中国', None),
        ('腾势', 'Denza', 'https://www.denza.com', '豪华', '中国', '比亚迪'),
        ('方程豹', 'Fangchengbao', 'https://www.fangchengbao.com', '豪华', '中国', '比亚迪'),
        ('理想汽车', 'Li Auto', 'https://www.lixiang.com', '新势力', '中国', None),
        ('吉利汽车', 'Geely', 'https://www.geely.com', '传统', '中国', None),
        ('极氪', 'Zeekr', 'https://www.zeekrlife.com', '新能源', '中国', '吉利'),
        ('小鹏汽车', 'Xpeng', 'https://www.xiaopeng.com', '新势力', '中国', None),
        ('蔚来', 'NIO', 'https://www.nio.cn', '新势力', '中国', None),
        ('问界', 'AITO', 'https://www.aito.com.cn', '新能源', '中国', '赛力斯'),
        ('零跑汽车', 'Leapmotor', 'https://www.leapmotor.com', '新势力', '中国', None),
        ('深蓝汽车', 'Deepal', 'https://www.deepal.com.cn', '新能源', '中国', '长安'),
        ('阿维塔', 'Avatr', 'https://www.avatr.com', '豪华', '中国', '长安'),
        ('智己汽车', 'IM', 'https://www.immotors.com', '新能源', '中国', '上汽'),
        ('特斯拉', 'Tesla', 'https://www.tesla.cn', '新能源', '美国', None),
        ('丰田', 'Toyota', 'https://www.toyota.com.cn', '传统', '日本', None),
        ('本田', 'Honda', 'https://www.honda.com.cn', '传统', '日本', None),
    ]
    
    for name, name_en, website, category, country, parent in brands:
        get_or_create_brand(name, name_en, website,
                           category=category, country=country, parent_brand=parent)


def init_db_full():
    """Initialize full database with all tables and default data."""
    init_db()
    init_brands()
    print("Database initialized with full schema and default brands.")


if __name__ == '__main__':
    init_db_full()
