"""Simple SQLite database for vehicle data."""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import DB_PATH


def init_db():
    """Initialize the database with required tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS brands (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        name_en TEXT,
        website TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY,
        brand_id INTEGER,
        name TEXT NOT NULL,
        segment TEXT,
        power_type TEXT,
        status TEXT,
        announce_date DATE,
        presale_date DATE,
        launch_date DATE,
        facelift_date DATE,
        image_urls TEXT,
        source_url TEXT,
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY,
        vehicle_id INTEGER,
        price_type TEXT,
        min_price DECIMAL,
        max_price DECIMAL,
        currency TEXT DEFAULT 'CNY',
        effective_date DATE,
        source_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
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
    ''')
    
    conn.commit()
    conn.close()


def get_connection():
    return sqlite3.connect(DB_PATH)


# Vehicle CRUD

def insert_vehicle(brand_id: int, name: str, **kwargs) -> int:
    """Insert a new vehicle and return its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    fields = ['brand_id', 'name']
    values = [brand_id, name]
    
    for key in ['segment', 'power_type', 'status', 'announce_date', 
                'presale_date', 'launch_date', 'facelift_date', 
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
    
    allowed = ['segment', 'power_type', 'status', 'announce_date',
               'presale_date', 'launch_date', 'facelift_date',
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


def list_vehicles(status: Optional[str] = None) -> List[Dict]:
    """List all vehicles, optionally filtered by status."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if status:
        cursor.execute("SELECT * FROM vehicles WHERE status = ? ORDER BY updated_at DESC", (status,))
    else:
        cursor.execute("SELECT * FROM vehicles ORDER BY updated_at DESC")
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# Price CRUD

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


# Crawled data CRUD

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


# Brand helpers

def get_or_create_brand(name: str, name_en: Optional[str] = None, 
                        website: Optional[str] = None) -> int:
    """Get brand ID or create if not exists."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM brands WHERE name = ?", (name,))
    row = cursor.fetchone()
    
    if row:
        brand_id = row[0]
    else:
        cursor.execute('''
            INSERT INTO brands (name, name_en, website) 
            VALUES (?, ?, ?)
        ''', (name, name_en, website))
        conn.commit()
        brand_id = cursor.lastrowid
    
    conn.close()
    return brand_id


def init_brands():
    """Initialize default brands."""
    brands = [
        ('小米汽车', 'Xiaomi Auto', 'https://www.xiaomiev.com'),
        ('比亚迪', 'BYD', 'https://www.byd.com'),
        ('理想汽车', 'Li Auto', 'https://www.lixiang.com'),
        ('吉利汽车', 'Geely', 'https://www.geely.com'),
        ('小鹏汽车', 'Xpeng', 'https://www.xiaopeng.com'),
        ('蔚来', 'NIO', 'https://www.nio.cn'),
        ('问界', 'AITO', 'https://www.aito.com.cn'),
        ('零跑汽车', 'Leapmotor', 'https://www.leapmotor.com'),
    ]
    
    for name, name_en, website in brands:
        get_or_create_brand(name, name_en, website)


if __name__ == '__main__':
    init_db()
    init_brands()
    print("Database initialized with default brands.")
