"""Export database to Obsidian-compatible Markdown vault.

Structure:
    obsidian/
    ├── Brands/          - Brand notes with YAML frontmatter
    ├── Vehicles/        - Vehicle notes with full specs
    ├── Competitors/     - Comparison matrices
    └── _templates/      - Note templates

Links:
    - Vehicle notes link to their brand: [[Brand Name]]
    - Brand notes list their vehicles: [[Vehicle Name]]
    - Competitor notes link both vehicles: [[Vehicle A]] vs [[Vehicle B]]
"""

import os
import sys
import json
import shutil
sys.path.insert(0, os.path.dirname(__file__))

from database import get_connection
from datetime import datetime


def sanitize_filename(name: str) -> str:
    """Make a string safe for use as filename."""
    return name.replace('/', '-').replace('\\', '-').replace(':', '-')


def create_obsidian_vault(output_dir: str = None) -> str:
    """Create Obsidian vault directory structure."""
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(__file__), '..', 'obsidian_vault'
        )
    
    # Create directories
    for subdir in ['Brands', 'Vehicles', 'Competitors', 'Daily', '_templates']:
        os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)
    
    return output_dir


def export_brands(vault_dir: str) -> dict:
    """Export all brands as Markdown notes.
    
    Returns:
        Dict mapping brand_id -> brand info
    """
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM brands ORDER BY id")
    brands = {row['id']: dict(row) for row in cursor.fetchall()}
    
    # Get vehicle counts per brand
    cursor.execute("""
        SELECT brand_id, COUNT(*) as count
        FROM vehicles
        GROUP BY brand_id
    """)
    vehicle_counts = {row['brand_id']: row['count'] for row in cursor.fetchall()}
    
    for brand_id, brand in brands.items():
        name = brand['name']
        filename = sanitize_filename(name) + '.md'
        filepath = os.path.join(vault_dir, 'Brands', filename)
        
        # YAML frontmatter
        fm = []
        fm.append('---')
        fm.append(f'type: brand')
        fm.append(f'name: {name}')
        fm.append(f'name_en: {brand.get("name_en", "")}')
        fm.append(f'category: {brand.get("category", "")}')
        fm.append(f'country: {brand.get("country", "")}')
        fm.append(f'parent_brand: {brand.get("parent_brand", "")}')
        fm.append(f'website: {brand.get("official_url", "")}')
        fm.append(f'vehicle_count: {vehicle_counts.get(brand_id, 0)}')
        fm.append('---')
        fm.append('')
        
        # Content
        fm.append(f"# {name}")
        fm.append('')
        fm.append(f"**{name}** ({brand.get('name_en', '')})")
        fm.append('')
        
        if brand.get('category'):
            fm.append(f"- 分类：{brand['category']}")
        if brand.get('country'):
            fm.append(f"- 国家：{brand['country']}")
        if brand.get('parent_brand'):
            fm.append(f"- 母公司：{brand['parent_brand']}")
        if brand.get('official_url'):
            fm.append(f"- 官网：[{brand['official_url']}]({brand['official_url']})")
        fm.append('')
        
        fm.append('## 旗下车型')
        fm.append('')
        
        # List vehicles for this brand
        cursor.execute("SELECT name FROM vehicles WHERE brand_id = ?", (brand_id,))
        vehicles = cursor.fetchall()
        for v in vehicles:
            fm.append(f"- [[{v['name']}]]")
        
        if not vehicles:
            fm.append('（暂无车型数据）')
        
        fm.append('')
        fm.append('---')
        fm.append(f'*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fm))
    
    conn.close()
    print(f"✅ Exported {len(brands)} brand notes to Brands/")
    return brands


def export_vehicles(vault_dir: str, brands: dict) -> dict:
    """Export all vehicles as Markdown notes."""
    conn = get_connection()
    conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT v.*, b.name as brand_name
        FROM vehicles v
        JOIN brands b ON v.brand_id = b.id
        ORDER BY v.id
    """)
    vehicles = {row['id']: dict(row) for row in cursor.fetchall()}
    
    for vid, v in vehicles.items():
        name = v['name']
        brand_name = v.get('brand_name', '')
        filename = sanitize_filename(name) + '.md'
        filepath = os.path.join(vault_dir, 'Vehicles', filename)
        
        # Get price
        cursor.execute("""
            SELECT min_price, max_price, price_type
            FROM prices
            WHERE vehicle_id = ?
            ORDER BY effective_date DESC
            LIMIT 1
        """, (vid,))
        price_row = cursor.fetchone()
        
        # Get specs (latest)
        cursor.execute("SELECT * FROM vehicle_specs WHERE vehicle_id = ? ORDER BY created_at DESC LIMIT 1", (vid,))
        spec_row = cursor.fetchone()
        
        # YAML frontmatter
        fm = []
        fm.append('---')
        fm.append('type: vehicle')
        fm.append(f'name: {name}')
        fm.append(f'brand: "[[{brand_name}]]"')
        fm.append(f'status: {v.get("status", "")}')
        
        if v.get('segment'):
            fm.append(f'segment: {v["segment"]}')
        if v.get('body_type'):
            fm.append(f'body_type: {v["body_type"]}')
        if v.get('power_type'):
            fm.append(f'power_type: {v["power_type"]}')
        if v.get('platform'):
            fm.append(f'platform: {v["platform"]}')
        
        # Dates
        if v.get('announce_date'):
            fm.append(f'announce_date: {v["announce_date"]}')
        if v.get('presale_date'):
            fm.append(f'presale_date: {v["presale_date"]}')
        if v.get('launch_date'):
            fm.append(f'launch_date: {v["launch_date"]}')
        
        # Price
        if price_row:
            fm.append(f'price_min: {price_row["min_price"]}')
            fm.append(f'price_max: {price_row["max_price"]}')
            fm.append(f'price_type: {price_row["price_type"]}')
        
        # Dimensions
        if v.get('length'):
            fm.append(f'length: {v["length"]}')
        if v.get('width'):
            fm.append(f'width: {v["width"]}')
        if v.get('height'):
            fm.append(f'height: {v["height"]}')
        if v.get('wheelbase'):
            fm.append(f'wheelbase: {v["wheelbase"]}')
        
        # Tags
        if v.get('tags'):
            tags = [t.strip() for t in v['tags'].split(',')]
            fm.append(f'tags: {json.dumps(tags, ensure_ascii=False)}')
        
        fm.append('---')
        fm.append('')
        
        # Content
        fm.append(f"# {name}")
        fm.append('')
        fm.append(f"品牌：[[{brand_name}]]")
        fm.append('')
        
        # Overview
        status = v.get('status', '')
        launch = v.get('launch_date') or v.get('presale_date') or '待定'
        
        overview = f"{name}是[[{brand_name}]]旗下的"
        if v.get('segment'):
            overview += v['segment']
        if v.get('power_type'):
            overview += f"，{v['power_type']}"
        overview += "车型。"
        
        if status:
            overview += f"当前状态：**{status}**。"
        if launch != '待定':
            overview += f"预计{launch}上市。"
        
        fm.append(overview)
        fm.append('')
        
        # Price section
        if price_row:
            min_p = price_row['min_price']
            max_p = price_row['max_price']
            price_str = f"{min_p}万" if min_p == max_p else f"{min_p}-{max_p}万"
            fm.append(f"**{price_row['price_type']}**：{price_str}")
            fm.append('')
        
        # Dimensions
        if v.get('length') and v.get('width') and v.get('height'):
            fm.append(f"**车身尺寸**：{v['length']}×{v['width']}×{v['height']}mm")
        if v.get('wheelbase'):
            fm.append(f"**轴距**：{v['wheelbase']}mm")
        if v.get('length') or v.get('wheelbase'):
            fm.append('')
        
        # Specs
        if spec_row:
            fm.append('## 核心参数')
            fm.append('')
            
            if spec_row.get('motor_power'):
                fm.append(f"- 动力：{spec_row['motor_power']} {spec_row.get('motor_type', '')}")
            if spec_row.get('motor_torque'):
                fm.append(f"- 扭矩：{spec_row['motor_torque']}")
            if spec_row.get('drivetrain'):
                fm.append(f"- 驱动：{spec_row['drivetrain']}")
            if spec_row.get('battery_capacity'):
                fm.append(f"- 电池：{spec_row['battery_capacity']}kWh {spec_row.get('battery_type', '')}")
            if spec_row.get('battery_brand'):
                fm.append(f"- 电芯：{spec_row['battery_brand']}")
            if spec_row.get('range_cltc'):
                fm.append(f"- 续航(CLTC)：{spec_row['range_cltc']}km")
            if spec_row.get('charging_time'):
                fm.append(f"- 快充：{spec_row['charging_time']}")
            if spec_row.get('chip'):
                fm.append(f"- 智驾芯片：{spec_row['chip']}")
            if spec_row.get('radar'):
                fm.append(f"- 感知硬件：{spec_row['radar']}")
            if spec_row.get('suspension_front') and spec_row.get('suspension_rear'):
                fm.append(f"- 悬架：前{spec_row['suspension_front']}+后{spec_row['suspension_rear']}")
            
            fm.append('')
        
        # Tags / Highlights
        if v.get('tags'):
            fm.append('## 亮点配置')
            fm.append('')
            tags = [t.strip() for t in v['tags'].split(',')]
            for tag in tags:
                fm.append(f"- {tag}")
            fm.append('')
        
        # Competitors
        cursor.execute("""
            SELECT v.name, c.relationship_type, c.notes
            FROM competitors c
            JOIN vehicles v ON c.competitor_vehicle_id = v.id
            WHERE c.vehicle_id = ?
        """, (vid,))
        comps = cursor.fetchall()
        
        if comps:
            fm.append('## 竞品车型')
            fm.append('')
            for c in comps:
                fm.append(f"- [[{c['name']}]] ({c['relationship_type']})")
                if c['notes']:
                    fm.append(f"  - {c['notes']}")
            fm.append('')
        
        # Source
        if v.get('source_url'):
            fm.append(f"**来源**：[{v['source_url']}]({v['source_url']})")
            fm.append('')
        
        fm.append('---')
        fm.append(f'*Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}*')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fm))
    
    conn.close()
    print(f"✅ Exported {len(vehicles)} vehicle notes to Vehicles/")
    return vehicles


def create_dataview_queries(vault_dir: str):
    """Create Obsidian Dataview query examples."""
    queries_dir = os.path.join(vault_dir, '_queries')
    os.makedirs(queries_dir, exist_ok=True)
    
    # Query: All vehicles by price
    query1 = """# 按价格排序的车型

```dataview
TABLE price_type, price_min, price_max, brand, status
FROM "Vehicles"
SORT price_min ASC
```
"""
    
    with open(os.path.join(queries_dir, '按价格排序.md'), 'w', encoding='utf-8') as f:
        f.write(query1)
    
    # Query: Upcoming launches
    query2 = """# 即将上市车型

```dataview
TABLE launch_date, brand, price_min, price_max
FROM "Vehicles"
WHERE status = "预售" OR status = "confirmed"
SORT launch_date ASC
```
"""
    
    with open(os.path.join(queries_dir, '即将上市.md'), 'w', encoding='utf-8') as f:
        f.write(query2)
    
    # Query: Vehicles with Lidar
    query3 = """# 带激光雷达的车型

```dataview
TABLE brand, price_min, price_max
FROM "Vehicles"
WHERE contains(tags, "激光雷达")
SORT price_min ASC
```
"""
    
    with open(os.path.join(queries_dir, '激光雷达车型.md'), 'w', encoding='utf-8') as f:
        f.write(query3)
    
    print(f"✅ Created 3 Dataview queries in _queries/")


def export_daily_article(vault_dir: str):
    """Copy today's article to Obsidian Daily folder."""
    daily_dir = os.path.join(vault_dir, 'Daily')
    
    # Copy latest article
    src_article = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'export',
        datetime.now().strftime('%Y%m%d'), 'article_laotu_style.md'
    )
    
    if os.path.exists(src_article):
        date_str = datetime.now().strftime('%Y-%m-%d')
        dest = os.path.join(daily_dir, f'{date_str}.md')
        shutil.copy2(src_article, dest)
        print(f"✅ Copied today's article to Daily/{date_str}.md")
    else:
        print("⚠️ No article found for today")


def main():
    """Run full Obsidian export."""
    print("=" * 60)
    print("Obsidian Vault Export")
    print("=" * 60)
    
    vault_dir = create_obsidian_vault()
    print(f"📁 Vault: {vault_dir}")
    print()
    
    # Export brands
    brands = export_brands(vault_dir)
    print()
    
    # Export vehicles
    vehicles = export_vehicles(vault_dir, brands)
    print()
    
    # Create Dataview queries
    create_dataview_queries(vault_dir)
    print()
    
    # Copy daily article
    export_daily_article(vault_dir)
    print()
    
    print("=" * 60)
    print("✅ Obsidian vault export complete!")
    print("=" * 60)
    print(f"\nOpen {vault_dir} as an Obsidian vault to browse.")
    print("\nFeatures:")
    print("  • Brands/      - Brand notes with vehicle links")
    print("  • Vehicles/    - Full vehicle specs with brand links")
    print("  • _queries/    - Dataview query examples")
    print("  • Daily/       - Generated articles")
    print("\nTip: Install 'Dataview' plugin in Obsidian for powerful queries.")


if __name__ == '__main__':
    main()
