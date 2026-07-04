"""AI Content Generator for Auto Intelligence Center.

Features:
- Jinja2 template-based content generation (no API required for basic output)
- Optional LLM integration for enhanced analysis
- Prompt templates stored in prompts/ directory
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader, Template

from database import list_vehicles, get_latest_price

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'prompts')
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')


class ContentGenerator:
    """Generate content for all four columns using templates and optional LLM."""
    
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        # Templates for direct content rendering
        self.template_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
        # Prompts for LLM enhancement
        self.prompt_env = Environment(loader=FileSystemLoader(PROMPTS_DIR))
        
        # Load prompt templates
        self.prompts = {}
        for prompt_file in os.listdir(PROMPTS_DIR):
            if prompt_file.endswith('.md'):
                name = prompt_file.replace('.md', '')
                with open(os.path.join(PROMPTS_DIR, prompt_file)) as f:
                    self.prompts[name] = f.read()
    
    def _render_template(self, template_name: str, **kwargs) -> str:
        """Render a Jinja2 template from templates directory."""
        try:
            template = self.template_env.get_template(f'{template_name}.md')
            return template.render(**kwargs)
        except Exception as e:
            print(f"Template error for {template_name}: {e}")
            return ""
    
    def generate_daily(self, vehicles: List[Dict]) -> str:
        """Generate daily new cars column."""
        if not vehicles:
            return "**今日新车（Daily）**\n\n今日暂无新车动态。"
        
        daily_cars = []
        for v in vehicles[:5]:
            price_info = get_latest_price(v['id'])
            price_str = None
            if price_info:
                min_p = price_info['min_price']
                max_p = price_info['max_price']
                price_str = f"{min_p:.1f}" if min_p == max_p else f"{min_p:.1f}-{max_p:.1f}"
            
            daily_cars.append({
                'name': v['name'],
                'date': v.get('launch_date') or v.get('presale_date') or '待定',
                'price': price_str,
                'highlights': v.get('tags', '配置待公布')[:30],
                'drawbacks': '暂无',  # Would need review data
                'review': '★★★★☆ 值得关注',
            })
        
        return self._render_template('daily_new_car', vehicle_data=daily_cars[0] if daily_cars else {})
    
    def generate_calendar(self, vehicles: List[Dict]) -> str:
        """Generate new car calendar."""
        today = datetime.now()
        this_week_end = today + timedelta(days=7)
        this_month_end = today + timedelta(days=30)
        next_month_start = this_month_end + timedelta(days=1)
        next_month_end = today + timedelta(days=60)
        
        this_week = []
        this_month = []
        next_month = []
        
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
                elif next_month_start <= ld <= next_month_end:
                    next_month.append(car_info)
            except (ValueError, TypeError):
                continue
        
        return self._render_template('new_car_calendar',
                                     this_week=this_week,
                                     this_month=this_month,
                                     next_month=next_month)
    
    def generate_price_changes(self, vehicles: List[Dict]) -> str:
        """Generate price change column."""
        changes = self._find_price_changes(vehicles)
        
        if not changes:
            return "**价格变化（Price）**\n\n今日暂无价格变动。"
        
        return self._render_template('price_change', price_changes=changes)
    
    def generate_reviews(self, vehicles: List[Dict]) -> str:
        """Generate one-sentence reviews."""
        if not vehicles:
            return "**编辑观点**\n\n暂无车型点评。"
        
        review_cars = []
        for v in vehicles[:5]:
            review_cars.append({
                'name': v['name'],
                'rating': '★★★★☆',
                'review': '值得关注的车型，建议等更多信息公布后再做决定。',
            })
        
        return self._render_template('one_sentence_review', vehicles=review_cars)
    
    def generate_all(self, vehicles: Optional[List[Dict]] = None) -> Dict[str, str]:
        """Generate all four columns."""
        if vehicles is None:
            vehicles = list_vehicles()
        
        return {
            'daily': self.generate_daily(vehicles),
            'calendar': self.generate_calendar(vehicles),
            'price': self.generate_price_changes(vehicles),
            'review': self.generate_reviews(vehicles),
        }
    
    def _find_price_changes(self, vehicles: List[Dict]) -> List[Dict]:
        """Find vehicles with price changes."""
        from database import get_connection
        
        changes = []
        conn = get_connection()
        conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
        cursor = conn.cursor()
        
        for v in vehicles:
            cursor.execute('''
                SELECT * FROM prices 
                WHERE vehicle_id = ? 
                ORDER BY effective_date DESC, created_at DESC 
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
                    'old_price': f"{previous['min_price']:.1f}",
                    'new_type': latest['price_type'],
                    'new_price': f"{latest['min_price']:.1f}",
                    'change': f"{'↓' if change < 0 else '↑'}{abs(change):.1f}万",
                    'review': '价格诚意足够' if change < 0 else '建议观望',
                })
        
        conn.close()
        return changes
    
    def get_llm_prompt(self, column: str, data: Dict) -> str:
        """Get the raw prompt for LLM processing."""
        prompt_template = self.prompts.get(column, '')
        
        # Extract the prompt content (after frontmatter)
        if '---' in prompt_template:
            parts = prompt_template.split('---')
            if len(parts) >= 3:
                prompt_template = parts[2]
        
        # Render with data
        template = self.prompt_env.from_string(prompt_template)
        return template.render(**data)


if __name__ == '__main__':
    # Test content generation
    generator = ContentGenerator()
    
    # Test with sample data
    test_vehicles = [
        {
            'id': 1,
            'name': '小米YU9',
            'brand_id': 1,
            'segment': 'SUV',
            'power_type': '纯电',
            'status': '预售',
            'launch_date': '2026-07-15',
            'presale_date': '2026-07-01',
            'tags': '双电机四驱,激光雷达,8295芯片',
        },
        {
            'id': 2,
            'name': '比亚迪海豹06',
            'brand_id': 2,
            'segment': '轿车',
            'power_type': '插混',
            'status': 'confirmed',
            'launch_date': '2026-07-08',
            'tags': 'DM-i,续航1200km',
        },
        {
            'id': 3,
            'name': '零跑B10',
            'brand_id': 8,
            'segment': 'SUV',
            'power_type': '纯电',
            'status': 'confirmed',
            'launch_date': '2026-07-20',
            'tags': 'LEAP3.5架构,激光雷达',
        },
    ]
    
    results = generator.generate_all(test_vehicles)
    
    for column, content in results.items():
        print(f"\n{'='*50}")
        print(f"栏目：{column}")
        print('='*50)
        print(content)
