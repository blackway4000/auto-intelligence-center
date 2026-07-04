"""Data Collector for Auto Intelligence Center.

Integrates crawlers and stores structured data into the database.
Supports multiple sources: official websites, MIIT, media platforms.
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from database import (
    get_or_create_brand, insert_vehicle, insert_price, insert_specs,
    insert_content_source, add_competitor, find_potential_competitors,
    get_vehicle_by_name, list_vehicles, list_brands, update_vehicle,
    get_specs, get_latest_price,
)
from image_manager import ImageManager


class VehicleDataParser:
    """Parse raw crawl data into structured vehicle information."""
    
    # Common patterns for extracting price from text
    PRICE_PATTERNS = [
        r'(\d+\.?\d*)\s*万',  # "14.38万"
        r'起售价[:：]?\s*(\d+\.?\d*)',  # "起售价：14.38"
        r'售价[:：]?\s*(\d+\.?\d*)',  # "售价：14.38"
        r'(\d+\.?\d*)\s*万元',  # "14.38万元"
    ]
    
    # Vehicle name patterns (common naming conventions)
    NAME_PATTERNS = [
        r'(\w+\s*[A-Z]?\d{2,4})',  # "MONA L03", "YU9", "B10"
    ]
    
    @classmethod
    def extract_price(cls, text: str) -> Optional[float]:
        """Extract price from text."""
        if not text:
            return None
        for pattern in cls.PRICE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return float(match.group(1))
        return None
    
    @classmethod
    def extract_vehicle_name(cls, text: str, brand_name: str) -> Optional[str]:
        """Extract vehicle name from text."""
        if not text:
            return None
        
        # Try to find pattern like "Brand + Model"
        # e.g., "小鹏MONA L03", "小米YU9"
        for pattern in cls.NAME_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                full_name = f"{brand_name}{match}"
                if full_name in text or match in text:
                    return full_name
        
        return None
    
    @classmethod
    def parse_dimensions(cls, text: str) -> Dict[str, Optional[int]]:
        """Extract dimensions from text like '4650*1920*1600'."""
        result = {'length': None, 'width': None, 'height': None, 'wheelbase': None}
        
        # Pattern: 4650*1920*1600 or 4650×1920×1600
        dim_match = re.search(r'(\d{4,5})[\*×](\d{4})[\*×](\d{4})', text)
        if dim_match:
            result['length'] = int(dim_match.group(1))
            result['width'] = int(dim_match.group(2))
            result['height'] = int(dim_match.group(3))
        
        # Pattern: 轴距2850mm or 轴距 2850
        wb_match = re.search(r'轴距[:：]?\s*(\d{4,5})', text)
        if wb_match:
            result['wheelbase'] = int(wb_match.group(1))
        
        return result
    
    @classmethod
    def parse_power_info(cls, text: str) -> Dict[str, str]:
        """Extract power type and motor info from text."""
        result = {'power_type': '', 'motor_type': '', 'motor_power': ''}
        
        text_lower = text.lower()
        
        # Power type
        if '纯电' in text and '增程' in text:
            result['power_type'] = '纯电/增程'
        elif '增程' in text:
            result['power_type'] = '增程'
        elif '插混' in text or '混动' in text:
            result['power_type'] = '插混'
        elif '纯电' in text:
            result['power_type'] = '纯电'
        elif '燃油' in text:
            result['power_type'] = '燃油'
        
        # Motor power
        power_match = re.search(r'(\d+)\s*[Pp]s', text)
        if power_match:
            result['motor_power'] = f"{power_match.group(1)}Ps"
        
        # Motor type
        if '双电机' in text:
            result['motor_type'] = '双电机'
        elif '单电机' in text:
            result['motor_type'] = '单电机'
        elif '三电机' in text:
            result['motor_type'] = '三电机'
        
        return result
    
    @classmethod
    def parse_battery_info(cls, text: str) -> Dict[str, Optional[float]]:
        """Extract battery info from text."""
        result = {'capacity': None, 'brand': '', 'type': ''}
        
        # Capacity: 56度 or 56kWh
        cap_match = re.search(r'(\d+\.?\d*)\s*[度kK][Ww][Hh]?', text)
        if cap_match:
            result['capacity'] = float(cap_match.group(1))
        
        # Brand
        battery_brands = ['宁德时代', '比亚迪', '中创新航', '亿纬动力', '国轩高科']
        for brand in battery_brands:
            if brand in text:
                result['brand'] = brand
                break
        
        # Type
        if '磷酸铁锂' in text:
            result['type'] = '磷酸铁锂'
        elif '三元锂' in text:
            result['type'] = '三元锂'
        elif '固态' in text:
            result['type'] = '固态'
        
        return result


class DataCollector:
    """Main data collector that integrates sources and stores to database."""
    
    def __init__(self):
        self.parser = VehicleDataParser()
        self.image_manager = ImageManager()
    
    def add_vehicle_from_manual(self, brand_name: str, vehicle_name: str,
                                price_min: Optional[float] = None,
                                price_max: Optional[float] = None,
                                **kwargs) -> int:
        """Manually add a vehicle with full data (simulates crawler output)."""
        # Get or create brand
        brand_id = get_or_create_brand(brand_name)
        
        # Check if vehicle exists
        existing = get_vehicle_by_name(vehicle_name)
        if existing:
            vehicle_id = existing['id']
            # Update fields
            update_fields = {}
            for key in ['segment', 'body_type', 'power_type', 'platform', 'status',
                       'announce_date', 'presale_date', 'launch_date',
                       'length', 'width', 'height', 'wheelbase', 'tags']:
                if key in kwargs:
                    update_fields[key] = kwargs[key]
            if update_fields:
                from database import update_vehicle
                update_vehicle(vehicle_id, **update_fields)
        else:
            # Insert new vehicle
            vehicle_fields = {
                'segment': kwargs.get('segment'),
                'body_type': kwargs.get('body_type'),
                'power_type': kwargs.get('power_type'),
                'platform': kwargs.get('platform'),
                'status': kwargs.get('status', '预售'),
                'announce_date': kwargs.get('announce_date'),
                'presale_date': kwargs.get('presale_date'),
                'launch_date': kwargs.get('launch_date'),
                'length': kwargs.get('length'),
                'width': kwargs.get('width'),
                'height': kwargs.get('height'),
                'wheelbase': kwargs.get('wheelbase'),
                'tags': kwargs.get('tags'),
                'source_url': kwargs.get('source_url'),
            }
            # Remove None values
            vehicle_fields = {k: v for k, v in vehicle_fields.items() if v is not None}
            vehicle_id = insert_vehicle(brand_id, vehicle_name, **vehicle_fields)
        
        # Insert price if provided
        if price_min is not None:
            insert_price(vehicle_id, 
                        kwargs.get('price_type', '预售价'),
                        price_min, price_max,
                        effective_date=kwargs.get('price_date', datetime.now().strftime('%Y-%m-%d')),
                        source_url=kwargs.get('source_url'))
        
        # Insert specs if provided
        spec_fields = {}
        for key in ['motor_type', 'motor_power', 'motor_torque',
                    'battery_capacity', 'battery_brand', 'battery_type',
                    'range_cltc', 'range_wltc', 'range_nedc',
                    'charging_time', 'drivetrain',
                    'suspension_front', 'suspension_rear',
                    'adas_level', 'chip', 'radar', 'camera_count']:
            if key in kwargs:
                spec_fields[key] = kwargs[key]
        
        if spec_fields:
            insert_specs(vehicle_id, **spec_fields)
        
        # Insert content source if provided
        if kwargs.get('source_url'):
            insert_content_source(
                vehicle_id=vehicle_id,
                source_type=kwargs.get('source_type', 'official'),
                source_name=kwargs.get('source_name', '品牌官网'),
                source_url=kwargs.get('source_url'),
                title=kwargs.get('content_title', vehicle_name),
                content_summary=kwargs.get('content_summary'),
                publish_date=kwargs.get('publish_date'),
                images=kwargs.get('images', [])
            )
        
        # Download images if URLs provided
        image_urls = kwargs.get('image_urls', [])
        if image_urls:
            print(f"\n  下载图片 ({len(image_urls)} 张)...")
            downloaded = self.image_manager.download_vehicle_images(
                brand_name, vehicle_name, image_urls,
                referer=kwargs.get('source_url'),
                max_images=kwargs.get('max_images', 10)
            )
            print(f"  成功下载 {len([d for d in downloaded if d['status'] in ('downloaded', 'existing')])} 张")
            
            # Process images (remove watermarks)
            print(f"  处理图片...")
            processed = self.image_manager.process_images(brand_name, vehicle_name)
            print(f"  成功处理 {len(processed)} 张")
            
            # Update vehicle with image paths
            image_paths = self.image_manager.get_image_paths(brand_name, vehicle_name, max_count=10)
            if image_paths:
                update_vehicle(vehicle_id, image_urls=json.dumps(image_paths))
        
        return vehicle_id
    
    def build_competitor_map(self, vehicle_id: int) -> List[Dict]:
        """Find and add potential competitors for a vehicle."""
        potentials = find_potential_competitors(vehicle_id)
        added = []
        
        for candidate in potentials[:5]:  # Top 5 potential competitors
            competitor_id = candidate['id']
            success = add_competitor(
                vehicle_id, competitor_id,
                relationship_type='同级',
                notes=f"同细分市场：{candidate.get('segment', '')}"
            )
            if success:
                added.append(candidate)
        
        return added
    
    def get_vehicle_full_data(self, vehicle_id: int) -> Dict:
        """Get complete vehicle data including specs, prices, competitors."""
        from database import get_connection
        
        conn = get_connection()
        conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
        cursor = conn.cursor()
        
        # Get vehicle with brand info
        cursor.execute("""
            SELECT v.*, b.name as brand_name, b.category as brand_category
            FROM vehicles v
            JOIN brands b ON v.brand_id = b.id
            WHERE v.id = ?
        """, (vehicle_id,))
        vehicle = dict(cursor.fetchone()) if cursor.fetchone else None
        
        conn.close()
        
        if not vehicle:
            return {}
        
        # Get related data
        specs = get_specs(vehicle_id)
        price = get_latest_price(vehicle_id)
        from database import get_competitors
        competitors = get_competitors(vehicle_id)
        
        return {
            'vehicle': vehicle,
            'specs': specs,
            'price': price,
            'competitors': competitors,
        }
    
    def list_all_vehicles_with_brand(self) -> List[Dict]:
        """List all vehicles with brand information."""
        from database import get_connection
        
        conn = get_connection()
        conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT v.*, b.name as brand_name, b.category as brand_category
            FROM vehicles v
            JOIN brands b ON v.brand_id = b.id
            ORDER BY v.updated_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


if __name__ == '__main__':
    # Test: Add Xiaopeng MONA L03 with real data
    collector = DataCollector()
    
    print("=" * 60)
    print("测试数据采集：小鹏MONA L03")
    print("=" * 60)
    
    vehicle_id = collector.add_vehicle_from_manual(
        brand_name='小鹏汽车',
        vehicle_name='小鹏MONA L03',
        price_min=14.38,
        price_max=16.18,
        price_type='预售价',
        segment='紧凑型SUV',
        body_type='SUV',
        power_type='纯电/增程',
        status='预售',
        presale_date='2026-07-02',
        launch_date='2026-07-15',
        length=4650,
        width=1920,
        height=1600,
        wheelbase=2850,
        tags='图灵芯片,249Ps后驱,前麦弗逊后多连杆',
        motor_type='单电机',
        motor_power='249Ps',
        drivetrain='后驱',
        suspension_front='麦弗逊',
        suspension_rear='多连杆',
        chip='图灵',
        radar='超声波',
        source_url='https://www.xiaopeng.com/news/xxx',
        source_type='official',
        source_name='小鹏官网',
    )
    
    print(f"\n车型已入库，ID: {vehicle_id}")
    
    # Add another vehicle for competitor testing
    vehicle_id2 = collector.add_vehicle_from_manual(
        brand_name='零跑汽车',
        vehicle_name='零跑B10',
        price_min=10.98,
        price_max=12.98,
        price_type='预售价',
        segment='紧凑型SUV',
        body_type='SUV',
        power_type='纯电',
        status='预售',
        tags='激光雷达,LEAP3.5架构',
        chip='8650',
        source_url='https://www.leapmotor.com/news/xxx',
    )
    
    print(f"车型已入库，ID: {vehicle_id2}")
    
    # Build competitor map
    print("\n构建竞品关系...")
    competitors = collector.build_competitor_map(vehicle_id)
    print(f"为 小鹏MONA L03 找到 {len(competitors)} 个竞品")
    for c in competitors:
        print(f"  - {c['name']} ({c['brand_name']})")
    
    # List all vehicles
    print("\n" + "=" * 60)
    print("当前数据库中的所有车型")
    print("=" * 60)
    all_vehicles = collector.list_all_vehicles_with_brand()
    for v in all_vehicles:
        price_info = get_latest_price(v['id'])
        price_str = f"{price_info['min_price']:.1f}万" if price_info else '待定'
        print(f"  {v['name']} | {v['brand_name']} | {v['segment']} | {v['power_type']} | {price_str}")
    
    print("\n" + "=" * 60)
    print("品牌列表")
    print("=" * 60)
    brands = list_brands()
    for b in brands:
        print(f"  {b['name']} ({b['category']}, {b['country']})")
