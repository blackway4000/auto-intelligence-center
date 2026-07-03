"""Auto Intelligence Center - Configuration"""

import os

# Data paths
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
EXPORT_DIR = os.path.join(DATA_DIR, 'export')
DB_PATH = os.path.join(DATA_DIR, 'vehicles.db')

# Brand sources to crawl
BRAND_SOURCES = {
    'xiaomi': {
        'name': '小米汽车',
        'news_url': 'https://www.xiaomiev.com/news',
        'enabled': True,
    },
    'byd': {
        'name': '比亚迪',
        'news_url': 'https://www.byd.com/cn/news',
        'enabled': True,
    },
    'li_auto': {
        'name': '理想汽车',
        'news_url': 'https://www.lixiang.com/news',
        'enabled': True,
    },
    'geely': {
        'name': '吉利汽车',
        'news_url': 'https://www.geely.com/news',
        'enabled': True,
    },
}

# Crawler settings
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 2  # seconds between requests
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

# Content generation
CONTENT_TEMPLATES = {
    'daily_new_cars': 'templates/daily.md',
    'calendar': 'templates/calendar.md',
    'price_changes': 'templates/price.md',
}
