"""Simple SQLite database for vehicle data."""

import sqlite3
import os
from datetime import datetime

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
