"""AI Content Generator for Auto Intelligence Center.

Generates structured content from vehicle database using templates.
AI analysis integration is optional - templates work standalone.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from jinja2 import Template

from database import (
    get_connection, list_vehicles, get_latest_price,
    get_pending_crawled, mark_crawled_processed
)


class ContentGenerator:
    """Generate content for all four columns."""
    
    def __init__(self):
        self.templates = {
            'daily': self._daily_template(),
            'calendar': self._calendar_template(),
            'price': self._price_template(),
            'review': self._review_template(),
        }
    
    def _daily_template(self) -> Template:
        return Template('''今日新车（Daily）
{% for car in cars %}
○ {{ car.name }}
  发布时间：{{ car.date }}
  一句话：{{ car.summary }}
  {% if car.price %}价格：{{ car.price }}万{% endif %}
  {% if car.highlights %}亮点：{{ car.highlights }}{% endif %}
  {% if car.drawbacks %}槽点：{{ car.drawbacks }}{% endif %}
  观点：{{ car.review }}
{% endfor %}
''')
    
    def _calendar_template(self) -> Template:
        return Template('''新车日历（Calendar）

本周上市
{% for car in this_week %}
○ {{ car.name }}（{{ car.date }}）{% if car.is_confirmed %}✓{% endif %}
{% endfor %}

本月上市
{% for car in this_month %}
○ {{ car.name }}（{{ car.date }}）
{% endfor %}
''')
    
    def _price_template(self) -> Template:
        return Template('''价格变化（Price）

{% for item in price_changes %}
{{ item.name }}
  {% if item.old_price %}原{{ item.price_type }}：{{ item.old_price }}万{% endif %}
  {% if item.new_price %}{{ item.new_type }}：{{ item.new_price }}万{% endif %}
  {% if item.change %}变化：{{ item.change }}{% endif %}
  观点：{{ item.review }}
{% endfor %}
''')
    
    def _review_template(self) -> Template:
        return Template('''编辑观点

{% for car in cars %}
{{ car.name }}：{{ car.rating }}
{{ car.review }}
{% endfor %}
''')
    
    def generate_daily(self, cars: List[Dict]) -> str:
        """Generate daily new cars column."""
        return self.templates['daily'].render(cars=cars)
    
    def generate_calendar(self, vehicles: List[Dict]) -> str:
        """Generate new car calendar."""
        today = datetime.now()
        this_week_end = today + timedelta(days=7)
        this_month_end = today + timedelta(days=30)
        
        this_week = []
        this_month = []
        
        for v in vehicles:
            launch_date = v.get('launch_date')
            if not launch_date:
                continue
            
            try:
                ld = datetime.strptime(launch_date, '%Y-%m-%d')
                car_info = {
                    'name': v['name'],
                    'date': launch_date,
                    'is_confirmed': v.get('status') == 'confirmed'
                }
                
                if today <= ld <= this_week_end:
                    this_week.append(car_info)
                elif today <= ld <= this_month_end:
                    this_month.append(car_info)
            except (ValueError, TypeError):
                continue
        
        return self.templates['calendar'].render(
            this_week=this_week,
            this_month=this_month
        )
    
    def generate_price_changes(self, changes: List[Dict]) -> str:
        """Generate price change column."""
        return self.templates['price'].render(price_changes=changes)
    
    def generate_reviews(self, cars: List[Dict]) -> str:
        """Generate one-sentence reviews."""
        review_cars = []
        for car in cars:
            review_cars.append({
                'name': car['name'],
                'rating': car.get('rating', '★★★★☆'),
                'review': car.get('review', '值得关注的车型'),
            })
        return self.templates['review'].render(cars=review_cars)
    
    def generate_all(self, vehicles: Optional[List[Dict]] = None) -> Dict[str, str]:
        """Generate all four columns."""
        if vehicles is None:
            vehicles = list_vehicles()
        
        # Build daily cars from vehicles with launch/presale dates
        daily_cars = []
        for v in vehicles[:5]:
            price_info = get_latest_price(v['id'])
            price_str = None
            if price_info:
                price_str = f"{price_info['min_price']}-{price_info['max_price']}"
            
            daily_cars.append({
                'name': v['name'],
                'date': v.get('launch_date') or v.get('presale_date') or '待定',
                'summary': f"{v['name']}新动态",
                'price': price_str,
                'highlights': v.get('tags', ''),
                'drawbacks': '',
                'review': '★★★★☆ 值得关注',
            })
        
        # Find price changes (vehicles with multiple price records)
        price_changes = self._find_price_changes(vehicles)
        
        return {
            'daily': self.generate_daily(daily_cars),
            'calendar': self.generate_calendar(vehicles),
            'price': self.generate_price_changes(price_changes),
            'review': self.generate_reviews(daily_cars),
        }
    
    def _find_price_changes(self, vehicles: List[Dict]) -> List[Dict]:
        """Find vehicles with price changes."""
        changes = []
        conn = get_connection()
        cursor = conn.cursor()
        
        for v in vehicles:
            cursor.execute('''
                SELECT * FROM prices 
                WHERE vehicle_id = ? 
                ORDER BY effective_date DESC 
                LIMIT 2
            ''', (v['id'],))
            
            rows = cursor.fetchall()
            if len(rows) >= 2:
                latest = rows[0]
                previous = rows[1]
                
                change = latest['min_price'] - previous['min_price']
                changes.append({
                    'name': v['name'],
                    'price_type': previous['price_type'],
                    'old_price': previous['min_price'],
                    'new_type': latest['price_type'],
                    'new_price': latest['min_price'],
                    'change': f"{'+' if change > 0 else ''}{change:.1f}万",
                    'review': '价格调整，建议关注' if change < 0 else '价格上涨',
                })
        
        conn.close()
        return changes


class PromptBuilder:
    """Build prompts for LLM analysis."""
    
    @staticmethod
    def vehicle_summary_prompt(vehicle_data: Dict) -> str:
        """Build prompt for generating vehicle summary."""
        return f"""你是一位资深汽车编辑。请根据以下车型数据，生成一段100字以内的"一句话点评"。

车型：{vehicle_data.get('name', '')}
品牌：{vehicle_data.get('brand', '')}
价格区间：{vehicle_data.get('price', '待定')}
动力类型：{vehicle_data.get('power_type', '')}
状态：{vehicle_data.get('status', '')}

要求：
1. 给出1-5星评分（用★表示）
2. 一句话总结适合谁买
3. 一句话给出购买建议
4. 指出最大的优点和最大的遗憾

输出格式：
评分：★★★★☆
适合人群：...
购买建议：...
最大优点：...
最大遗憾：...
"""


if __name__ == '__main__':
    # Test content generation
    generator = ContentGenerator()
    
    # Sample test data
    test_vehicles = [
        {
            'id': 1,
            'name': '小米YU9',
            'brand': '小米汽车',
            'power_type': '纯电',
            'status': '预售',
            'launch_date': '2026-07-15',
            'tags': '双电机四驱,激光雷达,8295芯片',
        },
        {
            'id': 2,
            'name': '比亚迪海豹06',
            'brand': '比亚迪',
            'power_type': '插混',
            'status': '上市',
            'launch_date': '2026-07-08',
            'tags': 'DM-i,续航1200km',
        },
    ]
    
    results = generator.generate_all(test_vehicles)
    
    for column, content in results.items():
        print(f"\n{'='*40}")
        print(f"栏目：{column}")
        print('='*40)
        print(content)
