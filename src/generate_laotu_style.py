"""Generate article in 老图 (图说汽车) style with competitor comparison.

Improvements:
- Competitor-aware reviews (no more identical 5-star ratings)
- Market positioning context ("10万级纯电SUV")
- Version buying advice per vehicle
- Cross-vehicle comparison paragraphs
"""

import os
import sys
import json
sys.path.insert(0, os.path.dirname(__file__))

from database import get_connection, list_vehicles
from ai_generator import CopyEngine
from image_manager import ImageManager
from datetime import datetime


def get_vehicle_full(vehicle_id: int) -> dict:
    """Get vehicle with brand, price, specs."""
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT v.*, b.name as brand_name
        FROM vehicles v
        JOIN brands b ON v.brand_id = b.id
        WHERE v.id = ?
    """, (vehicle_id,))
    row = cursor.fetchone()
    
    cursor.execute("""
        SELECT min_price, max_price, price_type
        FROM prices
        WHERE vehicle_id = ?
        ORDER BY effective_date DESC
        LIMIT 1
    """, (vehicle_id,))
    price_row = cursor.fetchone()
    
    cursor.execute("""
        SELECT * FROM vehicle_specs WHERE vehicle_id = ? ORDER BY created_at DESC LIMIT 1
    """, (vehicle_id,))
    spec_row = cursor.fetchone()
    
    # Get competitors
    cursor.execute("""
        SELECT v.name, v.brand_id, b.name as brand_name, c.relationship_type, c.notes
        FROM competitors c
        JOIN vehicles v ON c.competitor_vehicle_id = v.id
        JOIN brands b ON v.brand_id = b.id
        WHERE c.vehicle_id = ?
    """, (vehicle_id,))
    competitors = cursor.fetchall()
    
    conn.close()
    
    if not row:
        return {}
    
    result = dict(row)
    if price_row:
        result['min_price'] = price_row['min_price']
        result['max_price'] = price_row['max_price']
        result['price_type'] = price_row['price_type']
    if spec_row:
        result['specs'] = dict(spec_row)
    result['competitors'] = [dict(c) for c in competitors]
    
    return result


def get_market_position(price_val: float, segment: str, power_type: str) -> str:
    """Generate market positioning phrase."""
    if not price_val:
        return segment
    
    price_level = ""
    if price_val < 12:
        price_level = "10万级"
    elif price_val < 16:
        price_level = "15万级"
    elif price_val < 22:
        price_level = "20万级"
    elif price_val < 30:
        price_level = "25万级"
    else:
        price_level = "30万级以上"
    
    power_short = ""
    if '纯电' in power_type and '增程' in power_type:
        power_short = "纯电/增程"
    elif '纯电' in power_type:
        power_short = "纯电"
    elif '增程' in power_type:
        power_short = "增程"
    elif '插混' in power_type:
        power_short = "插混"
    
    seg_short = segment.replace('紧凑型', '').replace('中型', '').replace('大型', '')
    
    if power_short and seg_short:
        return f"{price_level}{power_short}{seg_short}"
    return f"{price_level}{segment}"


def generate_competitor_comparison(v: dict, all_vehicles: list) -> str:
    """Generate comparison text against competitors in the same article."""
    comps_in_article = []
    for comp in v.get('competitors', []):
        for av in all_vehicles:
            if av['name'] == comp['name']:
                comps_in_article.append(av)
                break
    
    if not comps_in_article:
        return ""
    
    v_price = float(v['min_price']) if v.get('min_price') else 0
    v_tags = v.get('tags', '')
    v_power = v.get('power_type', '')
    
    lines = []
    for comp in comps_in_article:
        comp_price = float(comp['min_price']) if comp.get('min_price') else 0
        comp_name = comp['name']
        comp_tags = comp.get('tags', '')
        
        price_diff = abs(v_price - comp_price)
        
        # Determine relative positioning
        if v_price > comp_price:
            if price_diff >= 3:
                advantages = []
                comp_power = comp.get('power_type', '')
                if '增程' in v_power and '增程' not in comp_power:
                    advantages.append("多了增程版本可选")
                if '激光雷达' in v_tags and '激光雷达' not in comp_tags:
                    advantages.append("智驾硬件更强")
                if '图灵' in v_tags and '图灵' not in comp_tags:
                    advantages.append("芯片方案更先进")
                
                if advantages:
                    lines.append(f"比同级的{comp_name}贵了{price_diff:.1f}万左右，主要贵在{'、'.join(advantages)}。")
                else:
                    lines.append(f"比同级的{comp_name}贵了{price_diff:.1f}万左右，具体值不值还得看实际体验。")
            else:
                lines.append(f"和{comp_name}价格接近，属于直接竞品，怎么选主要看你对品牌的偏好。")
        elif v_price < comp_price:
            if price_diff >= 3:
                advantages = []
                if '激光雷达' in v_tags and '激光雷达' not in comp_tags:
                    advantages.append("智驾配置")
                if '8650' in v_tags or '8295' in v_tags:
                    advantages.append("芯片规格")
                if '续航' in str(comp.get('specs', {}).get('range_cltc', '')) and v.get('specs', {}).get('range_cltc'):
                    v_range = str(v['specs'].get('range_cltc', ''))
                    c_range = str(comp.get('specs', {}).get('range_cltc', ''))
                    # Simple comparison
                
                if advantages:
                    lines.append(f"比{comp_name}便宜{price_diff:.1f}万，但在{'、'.join(advantages)}上并不逊色。")
                else:
                    lines.append(f"比{comp_name}便宜{price_diff:.1f}万，性价比优势很明显。")
            else:
                lines.append(f"和{comp_name}价格重叠，两台车会直接竞争。")
    
    return '\n\n'.join(lines) if lines else ""


def generate_differentiated_review(v: dict, all_vehicles: list) -> str:
    """Generate review that considers other vehicles in the same article."""
    name = v['name']
    price_val = float(v['min_price']) if v.get('min_price') else None
    tags = v.get('tags', '')
    power = v.get('power_type', '')
    segment = v.get('segment', '')
    
    # Base review from CopyEngine
    base_review = CopyEngine.generate_review(name, price_val, tags, power, segment)
    stars = base_review[:6] if base_review.startswith('★') else '★★★★☆'
    
    # Find other vehicles in same article as potential competitors
    other_vehicles = [av for av in all_vehicles if av['name'] != name]
    if not other_vehicles:
        return base_review
    
    v_price = price_val or 0
    v_segment = segment or ''
    
    for comp in other_vehicles:
        comp_price = float(comp['min_price']) if comp.get('min_price') else 0
        comp_tags = comp.get('tags', '')
        comp_power = comp.get('power_type', '')
        comp_segment = comp.get('segment', '')
        
        # Only compare if same segment
        if v_segment != comp_segment:
            continue
        
        # Cheaper with strong features -> emphasize value
        if v_price < comp_price - 2:
            if '激光雷达' in tags and '激光雷达' not in comp_tags:
                return f"{stars} 同价位配置最卷，智驾硬件没对手"
            if '8650' in tags and '8650' not in comp_tags:
                return f"{stars} 芯片规格越级，性价比优势明显"
            if price_val and price_val < 12:
                return f"{stars} 10万级闭眼入，这配置没理由拒绝"
            return f"{stars} 比竞品便宜{abs(v_price - comp_price):.0f}万，配置不缩水"
        
        # More expensive -> justify the premium
        if v_price > comp_price + 2:
            if '增程' in power and '增程' not in comp_power:
                return f"{stars} 能油能电，想一车多用的首选"
            if '图灵' in tags and '图灵' not in comp_tags:
                return f"{stars} 智驾方案更成熟，贵得有道理"
            return f"{stars} 品牌溢价有，但产品力对得起价格"
    
    return base_review


def generate_version_advice(v: dict) -> str:
    """Generate version buying advice based on specs."""
    name = v['name']
    price_min = float(v['min_price']) if v.get('min_price') else None
    price_max = float(v['max_price']) if v.get('max_price') else None
    tags = v.get('tags', '')
    specs = v.get('specs', {})
    
    if not price_min:
        return ""
    
    # Check for dual motor / performance version
    motor_power = specs.get('motor_power', '')
    if '/' in motor_power:
        # Multiple power options
        return f"\n{name}有多个动力版本，如果城市通勤为主，标准功率版够用了；想要更强加速就选高功率版，但差价如果超过1.5万，建议再掂量掂量。"
    
    # Check for lidar / chip tiers
    if '激光雷达' in tags:
        return f"\n带激光雷达的版本智驾能力更强，但入门版如果也有基础L2，日常也够用了。建议根据实际通勤路况决定，经常跑高速可以上高配。"
    
    # Price-based advice
    if price_min < 12:
        return f"\n{name}入门版性价比够高，但如果预算够，建议上中配，多出的配置值回票价。"
    
    return ""


def generate_laotu_article(vehicle_ids: list = None, output_dir: str = None) -> str:
    """Generate a full article in 老图 style with competitor awareness."""
    
    if vehicle_ids is None:
        vehicles = list_vehicles(status='预售')[:5]
        if not vehicles:
            vehicles = list_vehicles()[:5]
        vehicle_ids = [v['id'] for v in vehicles]
    
    vehicles = [get_vehicle_full(vid) for vid in vehicle_ids]
    vehicles = [v for v in vehicles if v]
    
    if not vehicles:
        return "暂无新车信息。"
    
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'export', datetime.now().strftime('%Y%m%d'))
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'images'), exist_ok=True)
    
    date_str = datetime.now().strftime('%Y年%m月%d日')
    lines = []
    
    # ===== Title =====
    lines.append(f"# {date_str}新车日报")
    lines.append("")
    
    # ===== Opening =====
    names = [v['name'] for v in vehicles]
    if len(names) == 1:
        opening = f"今天给大家带来{names[0]}的最新消息，这可能是你最近比较关注的一台车，咱们直接说重点。"
    elif len(names) == 2:
        opening = f"今天的新车信息不少，{names[0]}和{names[1]}都有新动态，两台车定位接近，属于直接竞品，咱们一个个来说。"
    else:
        opening = f"今天的新车信息不少，{'、'.join(names)}都有新动态，咱们一个个来说。"
    
    lines.append(opening)
    lines.append("")
    
    # ===== Vehicle blocks =====
    img_index = 1
    for v in vehicles:
        name = v['name']
        brand = v.get('brand_name', '')
        
        # Price
        price_str = ""
        price_val = None
        if v.get('min_price'):
            min_p = float(v['min_price'])
            max_p = float(v.get('max_price', min_p))
            price_val = min_p
            price_type = v.get('price_type', '价格')
            price_str = f"{price_type}{min_p:.2f}万" if min_p == max_p else f"{price_type}{min_p:.2f}-{max_p:.2f}万"
        
        # Launch date
        launch = v.get('launch_date') or v.get('presale_date') or ''
        
        # Segment & power
        segment = v.get('segment', '')
        power = v.get('power_type', '')
        
        # Dimensions
        length = v.get('length')
        width = v.get('width')
        height = v.get('height')
        wheelbase = v.get('wheelbase')
        
        # Specs
        specs = v.get('specs', {})
        motor_power = specs.get('motor_power', '')
        drivetrain = specs.get('drivetrain', '')
        chip = specs.get('chip', '')
        battery = specs.get('battery_capacity', '')
        range_val = specs.get('range_cltc', '')
        
        # Tags
        tags = v.get('tags', '')
        
        # Market position
        market_pos = get_market_position(price_val, segment, power)
        
        # Images
        img_manager = ImageManager()
        brand_name = v.get('brand_name', '')
        image_paths = img_manager.get_image_paths(brand_name, name, max_count=3)
        
        export_img_refs = []
        import shutil
        base_dir = os.path.join(os.path.dirname(__file__), '..')
        for i, src_path in enumerate(image_paths[:3]):
            if src_path.startswith('../'):
                src_path = os.path.normpath(os.path.join(os.path.dirname(__file__), src_path))
            elif not os.path.isabs(src_path):
                src_path = os.path.join(base_dir, src_path)
            
            ext = os.path.splitext(src_path)[1]
            dest_name = f"img_{img_index:02d}{ext}"
            dest_path = os.path.join(output_dir, 'images', dest_name)
            if os.path.exists(src_path):
                shutil.copy2(src_path, dest_path)
                export_img_refs.append(f"images/{dest_name}")
                img_index += 1
        
        # ---- Subheading ----
        lines.append(f"**{name}**")
        lines.append("")
        
        # ---- Paragraph 1: Core info with market position ----
        p1_parts = []
        if market_pos:
            p1_parts.append(f"{market_pos}")
        if launch:
            p1_parts.append(f"预计{launch}上市")
        if price_str:
            p1_parts.append(f"{price_str}")
        
        p1 = f"{name}"
        if p1_parts:
            p1 += "，" + "，".join(p1_parts) + "。"
        else:
            p1 += "，新车信息刚释放不久。"
        
        # Add dimensions
        dim_parts = []
        if length and width and height:
            dim_parts.append(f"车身尺寸{length}×{width}×{height}mm")
        if wheelbase:
            dim_parts.append(f"轴距{wheelbase}mm")
        if dim_parts:
            p1 += f"{'，'.join(dim_parts)}，"
        
        lines.append(p1)
        lines.append("")
        
        # ---- Paragraph 2: Power, battery, range ----
        p2_parts = []
        if motor_power and drivetrain:
            p2_parts.append(f"搭载{motor_power} {drivetrain}")
        if battery:
            p2_parts.append(f"匹配{battery}kWh电池")
        if range_val:
            p2_parts.append(f"CLTC续航{range_val}km")
        if chip:
            p2_parts.append(f"智驾芯片用上了{chip}")
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
            chip_lower = chip.lower() if chip else ''
            motor_lower = motor_power.lower() if motor_power else ''
            drive_lower = drivetrain.lower() if drivetrain else ''
            interesting = [t for t in tag_list 
                          if t not in ['前麦弗逊后多连杆', '麦弗逊多连杆', '扭力梁']
                          and chip_lower not in t.lower()
                          and motor_lower not in t.lower()
                          and drive_lower not in t.lower()]
            if interesting:
                p2_parts.append(f"亮点配置包括{interesting[0]}")
        
        if p2_parts:
            lines.append(f"{'，'.join(p2_parts)}。")
            lines.append("")
        
        # ---- Paragraph 3: Competitor comparison ----
        comp_text = generate_competitor_comparison(v, vehicles)
        if comp_text:
            lines.append(comp_text)
            lines.append("")
        
        # ---- Paragraph 4: Review with differentiation ----
        review = generate_differentiated_review(v, vehicles)
        target = CopyEngine.generate_target_user(segment, price_val, power)
        
        p4 = ""
        if target:
            p4 += f"适合{target}。"
        
        if review.startswith('★'):
            verdict = review[6:].strip() if len(review) > 6 else review
            p4 += f"{verdict}"
        else:
            p4 += review
        
        lines.append(p4)
        lines.append("")
        
        # ---- Paragraph 5: Version advice ----
        version_tip = generate_version_advice(v)
        if version_tip:
            lines.append(version_tip.strip())
            lines.append("")
        
        # ---- Images ----
        if export_img_refs:
            lines.append("📷 车型实拍")
            lines.append("")
            for ref in export_img_refs[:2]:
                lines.append(f"![{name}]({ref})")
                lines.append("")
        
        lines.append("")
    
    # ===== Closing =====
    lines.append("**总结**")
    lines.append("")
    
    if len(vehicles) == 2:
        v1, v2 = vehicles[0], vehicles[1]
        p1_val = float(v1['min_price']) if v1.get('min_price') else 0
        p2_val = float(v2['min_price']) if v2.get('min_price') else 0
        
        if p1_val > p2_val:
            expensive, cheap = v1, v2
        else:
            expensive, cheap = v2, v1
        
        lines.append(f"今天{v1['name']}和{v2['name']}都有新动态，两台车都是紧凑型SUV，但价格差了不少。")
        lines.append("")
        lines.append(f"预算紧张、看重配置性价比的，{cheap['name']}更合适，{cheap['min_price']:.0f}万起就有激光雷达和8650芯片。")
        lines.append("")
        lines.append(f"想要增程兜底、智驾方案更成熟的，{expensive['name']}值得考虑，但得多花{abs(p1_val - p2_val):.0f}万左右。")
        lines.append("")
        lines.append("建议大家根据自己的通勤场景和预算做选择，别盲目追高配。")
    elif len(vehicles) == 1:
        name = vehicles[0]['name']
        lines.append(f"{name}值得关注，等更多信息出来再给大家详细分析。")
    else:
        lines.append(f"今天{'、'.join([v['name'] for v in vehicles])}都有新动态，可以说7月车市越来越热闹了。")
        lines.append("")
        lines.append("建议大家别急着下手，多对比多看，毕竟今年新车迭代速度太快，等等党永远不亏。")
    
    lines.append("")
    lines.append("*以上信息基于公开数据整理，具体以官方公布为准。*")
    
    article = "\n".join(lines)
    
    # Save
    output_path = os.path.join(output_dir, 'article_laotu_style.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(article)
    
    return article, output_path


if __name__ == '__main__':
    article, path = generate_laotu_article()
    print(article)
    print(f"\n{'='*60}")
    print(f"✅ 已保存到: {path}")
