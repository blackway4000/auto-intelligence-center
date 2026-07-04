"""Batch import real vehicle data with validation and source tracking.

Each vehicle must pass data validation before insertion.
All data includes source_url for credibility.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from data_validator import validate_before_insert, ValidationError
from data_collector import DataCollector
from database import add_competitor


def import_xiaomi_yu7():
    """Import 小米YU7 GT with full specs."""
    collector = DataCollector()
    
    data = {
        'brand_name': '小米汽车',
        'vehicle_name': '小米YU7 GT',
        'price_min': 38.99,
        'price_max': 38.99,
        'price_type': '指导价',
        'segment': '中大型SUV',
        'body_type': 'SUV',
        'power_type': '纯电',
        'platform': '800V碳化硅',
        'status': '在售',
        'launch_date': '2026-05-21',
        'length': 5015,
        'width': 2007,
        'height': 1597,
        'wheelbase': 3000,
        'tags': '激光雷达,800V,空气悬架,双电机四驱',
        'source_url': 'https://m.autohome.com.cn/config/spec/76544.html',
        'source_type': 'media',
        'source_name': '汽车之家',
    }
    
    specs = {
        'motor_type': '双电机',
        'motor_power': '738kW(1003Ps)',
        'motor_torque': '1068N·m',
        'battery_capacity': 101.7,
        'battery_brand': '宁德时代',
        'battery_type': '三元锂',
        'range_cltc': 705,
        'charging_time': '0.2小时(10%-80%)',
        'drivetrain': '四驱',
        'suspension_front': '双叉臂',
        'suspension_rear': '五连杆',
        'adas_level': 'L2',
        'chip': '英伟达Drive AGX Thor',
        'radar': '禾赛AT128激光雷达',
    }
    
    try:
        validate_before_insert(data, raise_on_error=True)
        vid = collector.add_vehicle_from_manual(**{**data, **specs})
        print(f"✅ 小米YU7 GT imported, ID: {vid}")
        return vid
    except ValidationError as e:
        print(f"❌ 小米YU7 GT validation failed:\n{e}")
        return None


def import_wenjie_m9():
    """Import 问界M9焕新版 with full specs."""
    collector = DataCollector()
    
    data = {
        'brand_name': '问界',
        'vehicle_name': '问界M9焕新版',
        'price_min': 47.98,
        'price_max': 65.98,
        'price_type': '指导价',
        'segment': '大型SUV',
        'body_type': 'SUV',
        'power_type': '纯电/增程',
        'platform': 'DMO',
        'status': '在售',
        'launch_date': '2026-03-15',
        'length': 5285,
        'width': 2026,
        'height': 1845,
        'wheelbase': 3125,
        'tags': '激光雷达,华为乾崑智驾,空气悬架,增程',
        'source_url': 'http://m.toutiao.com/group/7625921255702594111/',
        'source_type': 'media',
        'source_name': '今日头条',
    }
    
    specs = {
        'motor_type': '双电机',
        'motor_power': '220kW+277kW',
        'motor_torque': '待定',
        'battery_capacity': 42.0,
        'battery_brand': '宁德时代',
        'battery_type': '三元锂',
        'range_cltc': '225/315',
        'charging_time': '待定',
        'drivetrain': '四驱',
        'suspension_front': '双叉臂',
        'suspension_rear': '多连杆',
        'adas_level': 'L2+',
        'chip': '华为乾崑',
        'radar': '激光雷达',
    }
    
    try:
        validate_before_insert(data, raise_on_error=True)
        vid = collector.add_vehicle_from_manual(**{**data, **specs})
        print(f"✅ 问界M9焕新版 imported, ID: {vid}")
        return vid
    except ValidationError as e:
        print(f"❌ 问界M9焕新版 validation failed:\n{e}")
        return None


def import_avatr_09():
    """Import 阿维塔09 with available data."""
    collector = DataCollector()
    
    data = {
        'brand_name': '阿维塔',
        'vehicle_name': '阿维塔09',
        'price_min': 25.0,
        'price_max': 35.0,
        'price_type': '预售价',
        'segment': '中大型SUV',
        'body_type': 'SUV',
        'power_type': '纯电/增程',
        'platform': 'CHN',
        'status': '预售',
        'launch_date': '2026-07-20',
        'tags': '激光雷达,华为智驾,鸿蒙座舱',
        'source_url': 'https://www.avatr.com',
        'source_type': 'official',
        'source_name': '阿维塔官网',
    }
    
    try:
        validate_before_insert(data, raise_on_error=True)
        vid = collector.add_vehicle_from_manual(**data)
        print(f"✅ 阿维塔09 imported, ID: {vid}")
        return vid
    except ValidationError as e:
        print(f"❌ 阿维塔09 validation failed:\n{e}")
        return None


def build_competitor_relations():
    """Build competitor relationships between vehicles."""
    from database import get_vehicle_by_name
    
    # Define competitor pairs
    pairs = [
        ('小鹏MONA L03', '零跑B10', '同级'),
        ('小米YU7 GT', '问界M9焕新版', '同级'),
        ('小米YU7 GT', '阿维塔09', '同级'),
    ]
    
    for v1_name, v2_name, rel_type in pairs:
        v1 = get_vehicle_by_name(v1_name)
        v2 = get_vehicle_by_name(v2_name)
        
        if v1 and v2:
            success = add_competitor(v1['id'], v2['id'], rel_type)
            if success:
                print(f"✅ Competitor: {v1_name} vs {v2_name}")
            else:
                print(f"⚠️ Competitor already exists: {v1_name} vs {v2_name}")
        else:
            print(f"❌ Missing vehicle for competitor: {v1_name} vs {v2_name}")


def main():
    """Run batch import."""
    print("=" * 60)
    print("Batch Vehicle Import with Validation")
    print("=" * 60)
    print()
    
    # Import vehicles
    v1 = import_xiaomi_yu7()
    print()
    v2 = import_wenjie_m9()
    print()
    v3 = import_avatr_09()
    print()
    
    # Build competitor relationships
    print("=" * 60)
    print("Building Competitor Relationships")
    print("=" * 60)
    build_competitor_relations()
    print()
    
    print("=" * 60)
    print("Batch Import Complete!")
    print("=" * 60)
    print("\nTip: Run 'python export_obsidian.py' to sync to Obsidian vault.")


if __name__ == '__main__':
    main()
