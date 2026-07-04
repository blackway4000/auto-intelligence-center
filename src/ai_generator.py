"""AI Content Generator for Auto Intelligence Center.

Features:
- Jinja2 template-based content generation (no API required for basic output)
- Rule-based copy generation for headlines, reviews, and recommendations
- Optional LLM integration for enhanced analysis
- Prompt templates stored in prompts/ directory
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader, Template

from database import list_vehicles, get_latest_price

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'prompts')
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')


# ============ Rule Engine for Copy Generation ============

class CopyEngine:
    """Generate human-like copy based on vehicle data rules. No LLM required."""
    
    # Tag -> human-friendly description mapping
    TAG_TRANSLATIONS = {
        '激光雷达': '高阶智驾',
        '图灵芯片': '智驾芯片强',
        '8295芯片': '车机流畅',
        '8650芯片': '智驾硬件够',
        '双电机四驱': '操控稳',
        '单电机后驱': '后驱有驾驶感',
        '249Ps后驱': '后驱有驾驶感',
        '前麦弗逊后多连杆': '底盘舒适',
        '麦弗逊多连杆': '底盘舒适',
        '扭力梁': '底盘一般',
        '后轮转向': '好开灵活',
        '零重力座椅': '坐着舒服',
        '大电池': '续航扎实',
        '长续航': '续航够用',
        '闪充': '充电快',
        '800V': '充电快',
        '天神之眼': '智驾能打',
        '城区领航': '城区智驾',
        '高速领航': '高速省心',
        '空气悬架': '底盘高级',
        'CDC': '底盘舒适',
        'DM-i': '省油耐用',
        'LEAP3.5架构': '新平台',
    }
    
    OPENING_TEMPLATES = [
        "没想到啊，{name}突然来了，这价格一出，估计要把水搅浑！",
        "一觉醒来，{name}公布了价格，我跟你说，这操作真的服了。",
        "真的服了，{name}这波来得够突然，价格有没有惊喜？",
        "又来了！{name}刚刚发布，兄弟们，这价格能不能行？",
        " clear啊，{name}这价格一公布，同价位选手得瑟瑟发抖了。",
    ]
    
    @classmethod
    def generate_opening(cls, name: str) -> str:
        """Generate an emotional opening line."""
        return random.choice(cls.OPENING_TEMPLATES).format(name=name)
    
    @classmethod
    def generate_summary(cls, name: str, price: Optional[float], tags: str, 
                         power_type: str, segment: str) -> str:
        """Generate one-sentence spicy review."""
        tags_lower = tags.lower()
        
        # Price-based rules
        if price and price < 15:
            if '激光雷达' in tags or '智驾' in tags or '图灵' in tags:
                return "这价格真的服了，智驾卷到15万内"
            return "价格杀手，要把水搅浑"
        
        if price and price < 20:
            if '激光雷达' in tags or '图灵' in tags:
                return "配置拉满，诚意够狠"
            return "这价位该有的都有了"
        
        if price and price >= 30:
            return "冲高端，但价格有点飘"
        
        # Power-type rules
        if '增程' in power_type and '纯电' in power_type:
            return "能油能电，实用派狂喜"
        
        if '纯电' in power_type and '续航' in tags:
            return "续航扎实，城市通勤稳"
        
        # Segment rules
        if 'SUV' in segment and '紧凑' in segment:
            return "年轻人第一台SUV的有力选手"
        
        return "新车型来势汹汹"
    
    @classmethod
    def generate_highlights(cls, tags: str) -> str:
        """Convert technical tags to human-friendly highlights (max 3)."""
        if not tags or tags == '配置待公布':
            return '配置待公布'
        
        tag_list = [t.strip() for t in tags.split(',')]
        translated = []
        
        for tag in tag_list:
            # Direct match
            if tag in cls.TAG_TRANSLATIONS:
                translated.append(cls.TAG_TRANSLATIONS[tag])
            # Partial match
            else:
                for key, value in cls.TAG_TRANSLATIONS.items():
                    if key in tag:
                        translated.append(value)
                        break
                else:
                    # Keep original if no translation
                    if len(tag) <= 12:
                        translated.append(tag)
        
        # Deduplicate and limit to 3
        seen = set()
        result = []
        for t in translated:
            if t not in seen and len(result) < 3:
                seen.add(t)
                result.append(t)
        
        return '、'.join(result) if result else '配置待公布'
    
    @classmethod
    def generate_target_user(cls, segment: str, price: Optional[float], 
                            power_type: str) -> str:
        """Determine target audience based on vehicle attributes."""
        price_desc = ""
        if price:
            if price < 15:
                price_desc = "预算15万"
            elif price < 20:
                price_desc = "预算18万"
            elif price < 30:
                price_desc = "预算25万"
            else:
                price_desc = "预算35万"
        
        # Segment-based
        if '紧凑' in segment:
            user = "想要第一台车的年轻人"
        elif '中型' in segment:
            user = "追求品质的三口之家"
        elif '大型' in segment or '中大' in segment:
            user = "有二孩的大家庭"
        elif '轿车' in segment:
            user = "喜欢轿车驾驶感的用户"
        else:
            user = "看重实用的消费者"
        
        # Power-type refinement
        if '增程' in power_type:
            user += "、想一车多用"
        elif '纯电' in power_type:
            user += "、城市通勤为主"
        
        if price_desc:
            return f"{price_desc}、{user}"
        return user
    
    @classmethod
    def generate_review(cls, name: str, price: Optional[float], tags: str,
                       power_type: str, segment: str) -> str:
        """Generate final verdict with star rating."""
        has_lidar = '激光雷达' in tags or '图灵' in tags
        is_dual_power = '增程' in power_type and '纯电' in power_type
        
        # 5-star: exceptional value
        if price and price < 15 and has_lidar:
            return "★★★★★ 闭眼入，这价位没对手"
        
        if price and price < 15 and is_dual_power:
            return "★★★★★ 能油能电还便宜，闭眼入"
        
        # 4.5-star: strong recommendation
        if price and price < 20 and has_lidar and '多连杆' in tags:
            return "★★★★☆ 能买，但等正式上市再看有没有惊喜"
        
        # 4-star: good but with caveats
        if price and price < 20:
            return "★★★★☆ 价格诚意够，配置也不差，可以冲"
        
        if is_dual_power and price and price < 25:
            return "★★★★☆ 能油能电，实用派首选"
        
        # 3.5-star: wait and see
        if price and price >= 30:
            return "★★★☆☆ 再等等，竞品更卷，下半年更香"
        
        # 3-star: mediocre
        if '扭力梁' in tags and price and price > 15:
            return "★★★☆☆ 底盘一般，这价格有点飘"
        
        return "★★★★☆ 值得关注，等更多信息再拍板"
    
    @classmethod
    def generate_version_recommendation(cls, name: str, price: Optional[float],
                                       tags: str) -> str:
        """Generate version buying advice."""
        if not price:
            return ""
        
        if '图灵' in tags or '激光雷达' in tags:
            return f"\n💡 **版本建议**：{name}最值得买的不是入门版，而是带高阶智驾的中配。入门版智驾硬件砍太狠，后期升级受限，建议一步到位。"
        
        if price < 15:
            return f"\n💡 **版本建议**：{name}入门版性价比够高，但如果预算够，建议上中配，多出的配置值回票价。"
        
        return ""


class ContentGenerator:
    """Generate content for all four columns using templates and optional LLM."""
    
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self.copy_engine = CopyEngine()
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
        """Generate daily new cars column with rule-based copy for all vehicles."""
        if not vehicles:
            return "**今日新车（Daily）**\n\n今日暂无新车动态。"
        
        daily_cars = []
        for v in vehicles[:5]:
            # Support both database prices and inline test prices
            price_val = None
            price_str = None
            if 'min_price' in v:
                min_p = float(v['min_price'])
                max_p = float(v.get('max_price', min_p))
                price_val = min_p
                price_str = f"{min_p:.1f}" if min_p == max_p else f"{min_p:.1f}-{max_p:.1f}"
            else:
                price_info = get_latest_price(v['id'])
                if price_info:
                    min_p = price_info['min_price']
                    max_p = price_info['max_price']
                    price_val = float(min_p)
                    price_str = f"{min_p:.1f}" if min_p == max_p else f"{min_p:.1f}-{max_p:.1f}"
            
            # Use rule engine to generate copy
            tags = v.get('tags', '')
            segment = v.get('segment', '')
            power_type = v.get('power_type', '')
            name = v['name']
            
            summary = self.copy_engine.generate_summary(
                name, price_val, tags, power_type, segment
            )
            highlights = self.copy_engine.generate_highlights(tags)
            target_user = self.copy_engine.generate_target_user(
                segment, price_val, power_type
            )
            review = self.copy_engine.generate_review(
                name, price_val, tags, power_type, segment
            )
            
            # Parse image_urls
            images = []
            raw_images = v.get('image_urls')
            if raw_images:
                if isinstance(raw_images, str):
                    try:
                        images = json.loads(raw_images)
                    except json.JSONDecodeError:
                        images = [raw_images] if raw_images else []
                elif isinstance(raw_images, list):
                    images = raw_images
            
            daily_cars.append({
                'name': name,
                'date': v.get('launch_date') or v.get('presale_date') or '待定',
                'price': price_str or '待定',
                'summary': summary,
                'highlights': highlights,
                'target_user': target_user,
                'review': review,
                'images': images,
            })
        
        # Generate opening
        opening = ""
        if daily_cars:
            opening = self.copy_engine.generate_opening(daily_cars[0]['name'])
        
        # Render each vehicle block
        blocks = []
        for car in daily_cars:
            block = self._render_template('daily_new_car', vehicle_data=car)
            blocks.append(block)
        
        # Add version recommendation for first vehicle
        version_tip = ""
        if vehicles:
            v = vehicles[0]
            if 'min_price' in v:
                price_val = float(v['min_price'])
            else:
                price_info = get_latest_price(v['id'])
                price_val = float(price_info['min_price']) if price_info else None
            version_tip = self.copy_engine.generate_version_recommendation(
                v['name'], price_val, v.get('tags', '')
            )
        
        content = '\n\n'.join(blocks)
        if opening:
            content = f"{opening}\n\n{content}{version_tip}"
        
        return content
    
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
        """Generate one-sentence reviews with rule-based copy."""
        if not vehicles:
            return "**编辑观点**\n\n暂无车型点评。"
        
        review_cars = []
        for v in vehicles[:5]:
            # Support both database prices and inline test prices
            if 'min_price' in v:
                price_val = float(v['min_price'])
            else:
                price_info = get_latest_price(v['id'])
                price_val = float(price_info['min_price']) if price_info else None
            
            review = self.copy_engine.generate_review(
                v['name'], price_val, v.get('tags', ''), 
                v.get('power_type', ''), v.get('segment', '')
            )
            
            review_cars.append({
                'name': v['name'],
                'rating': review.split(' ')[0] if ' ' in review else '★★★★☆',
                'review': review.split(' ', 1)[1] if ' ' in review else review,
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
                
                # Rule-based review for price changes
                if change < 0:
                    if abs(change) >= 2:
                        review = "降得够狠，诚意有了，可以看看"
                    else:
                        review = "降了但没降到位，建议再等等"
                else:
                    review = "涨价？这操作真的服了，建议观望"
                
                changes.append({
                    'name': v['name'],
                    'price_type': previous['price_type'],
                    'old_price': f"{previous['min_price']:.1f}",
                    'new_type': latest['price_type'],
                    'new_price': f"{latest['min_price']:.1f}",
                    'change': f"{'↓' if change < 0 else '↑'}{abs(change):.1f}万",
                    'review': review,
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
