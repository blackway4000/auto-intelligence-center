"""Auto Intelligence Center - Configuration"""

import os

# Data paths
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
RAW_DIR = os.path.join(DATA_DIR, 'raw')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
EXPORT_DIR = os.path.join(DATA_DIR, 'export')
DB_PATH = os.path.join(DATA_DIR, 'vehicles.db')

# ============ Brand Sources ============
# Official brand websites to crawl
BRAND_SOURCES = {
    'xiaomi': {
        'name': '小米汽车',
        'news_url': 'https://www.xiaomiev.com',
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
    'xpeng': {
        'name': '小鹏汽车',
        'news_url': 'https://www.xiaopeng.com/news',
        'enabled': True,
    },
    'nio': {
        'name': '蔚来',
        'news_url': 'https://www.nio.cn/news',
        'enabled': True,
    },
    'aito': {
        'name': '问界',
        'news_url': 'https://www.aito.com.cn/news',
        'enabled': True,
    },
    'leapmotor': {
        'name': '零跑汽车',
        'news_url': 'https://www.leapmotor.com/news',
        'enabled': True,
    },
    'deepal': {
        'name': '深蓝汽车',
        'news_url': 'https://www.deepal.com.cn/news',
        'enabled': True,
    },
    'avatr': {
        'name': '阿维塔',
        'news_url': 'https://www.avatr.com/news',
        'enabled': True,
    },
    'zeekr': {
        'name': '极氪',
        'news_url': 'https://www.zeekrlife.com/news',
        'enabled': True,
    },
    'tesla': {
        'name': '特斯拉',
        'news_url': 'https://www.tesla.cn/news',
        'enabled': True,
    },
}

# ============ Multi-channel Content Sources ============
# Sources for building content database and competitor analysis
CONTENT_SOURCES = {
    'official': {
        'name': '品牌官网',
        'description': '品牌官方发布的新车信息、价格、配置',
        'priority': 1,
        'enabled': True,
    },
    'miit': {
        'name': '工信部公告',
        'description': '新车申报图、参数、尺寸等官方备案信息',
        'priority': 2,
        'enabled': True,
    },
    'media': {
        'name': '汽车媒体',
        'description': '汽车之家、懂车帝、易车等媒体的评测和报道',
        'priority': 3,
        'enabled': True,
    },
    'social': {
        'name': '社交平台',
        'description': '微博、小红书等平台的用户反馈和口碑',
        'priority': 4,
        'enabled': False,  # Phase 2
    },
}

# Specific media platforms
MEDIA_PLATFORMS = {
    'autohome': {
        'name': '汽车之家',
        'base_url': 'https://www.autohome.com.cn',
        'search_url': 'https://www.autohome.com.cn/#pvareaid=3311239',
        'enabled': True,
    },
    'dongchedi': {
        'name': '懂车帝',
        'base_url': 'https://www.dongchedi.com',
        'enabled': True,
    },
    'yiche': {
        'name': '易车',
        'base_url': 'https://www.yiche.com',
        'enabled': True,
    },
}

# ============ MIIT Configuration ============
MIIT_CONFIG = {
    'official_url': 'https://www.miit.gov.cn',
    'announcement_path': '/jgsj/jns/wjfb/art/2024/art_xxx.html',
    'autohome_miit_url': 'https://www.autohome.com.cn/news/202506/1xxxxxxxx.html',
    'enabled': True,
}

# ============ Crawler Settings ============
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 2  # seconds between requests
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'

# ============ Content Generation ============
CONTENT_TEMPLATES = {
    'daily_new_cars': 'templates/daily.md',
    'calendar': 'templates/calendar.md',
    'price_changes': 'templates/price.md',
}

# ============ Data Collection Schedule ============
# How often to crawl each source (in hours)
COLLECTION_SCHEDULE = {
    'brand_official': 6,    # Every 6 hours
    'miit': 24,             # Daily
    'media': 4,             # Every 4 hours
}

# ============ Export Settings ============
EXPORT_FORMATS = {
    'markdown': True,
    'wechat_html': False,   # Phase 2
}
