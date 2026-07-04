"""Generate article in 老图 (图说汽车) style.

Style characteristics:
- Paragraph-based, no bullet lists
- Bold model name as subheading
- Information woven into narrative
- Images interspersed with captions
- Conversational opening and closing
- Specific numbers embedded naturally
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
        SELECT * FROM vehicle_specs WHERE vehicle_id = ?
    """, (vehicle_id,))
    spec_row = cursor.fetchone()
    
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
    
    return result


def generate_laotu_article(vehicle_ids: list = None, output_dir: str = None) -> str:
    """Generate a full article in 老图 style."""
    
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
        opening = f"今天的新车信息不少，{names[0]}和{names[1]}都有新动态，咱们一个个来说。"
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
        
        # Tags
        tags = v.get('tags', '')
        
        # Images - use ImageManager to get actual file paths
        img_manager = ImageManager()
        brand_name = v.get('brand_name', '')
        image_paths = img_manager.get_image_paths(brand_name, name, max_count=3)
        
        # Copy images to export dir
        export_img_refs = []
        import shutil
        base_dir = os.path.join(os.path.dirname(__file__), '..')
        for i, src_path in enumerate(image_paths[:3]):
            # Resolve relative paths
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
        
        # ---- Paragraph 1: Core info ----
        p1_parts = []
        if launch:
            p1_parts.append(f"预计{launch}上市")
        if price_str:
            p1_parts.append(f"{price_str}")
        
        p1 = f"{name}"
        if p1_parts:
            p1 += "，" + "，".join(p1_parts) + "。"
        else:
            p1 += "，新车信息刚释放不久。"
        
        # Add dimensions if available
        dim_parts = []
        if length and width and height:
            dim_parts.append(f"车身尺寸{length}×{width}×{height}mm")
        if wheelbase:
            dim_parts.append(f"轴距{wheelbase}mm")
        if dim_parts:
            p1 += f"{'，'.join(dim_parts)}，"
        
        if segment:
            p1 += f"定位{segment}"
            if power:
                p1 += f"，{power}"
            p1 += "。"
        
        lines.append(p1)
        lines.append("")
        
        # ---- Paragraph 2: Power & smart driving ----
        p2_parts = []
        if motor_power and drivetrain:
            p2_parts.append(f"搭载{motor_power} {drivetrain}")
        if chip:
            p2_parts.append(f"智驾芯片用上了{chip}")
        if tags:
            tag_list = [t.strip() for t in tags.split(',')]
            # Pick most interesting tags, exclude duplicates with already-mentioned specs
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
        
        # ---- Paragraph 3: Opinion ----
        review = CopyEngine.generate_review(name, price_val, tags, power, segment)
        target = CopyEngine.generate_target_user(segment, price_val, power)
        
        p3 = ""
        if target:
            p3 += f"适合{target}。"
        
        # Extract star rating and verdict
        if review.startswith('★'):
            verdict = review[6:].strip() if len(review) > 6 else review
            p3 += f"{verdict}"
        else:
            p3 += review
        
        lines.append(p3)
        lines.append("")
        
        # ---- Images ----
        if export_img_refs:
            lines.append("📷 车型实拍")
            lines.append("")
            for ref in export_img_refs[:2]:  # Max 2 images per vehicle
                lines.append(f"![{name}]({ref})")
                lines.append("")
        
        lines.append("")
    
    # ===== Closing =====
    lines.append("**总结**")
    lines.append("")
    
    if len(vehicles) == 1:
        v = vehicles[0]
        name = v['name']
        price_val = float(v['min_price']) if v.get('min_price') else None
        tags = v.get('tags', '')
        version_tip = CopyEngine.generate_version_recommendation(name, price_val, tags)
        if version_tip:
            lines.append(version_tip.replace("\n", "").replace("💡 **版本建议**：", ""))
        else:
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
