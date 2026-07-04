"""Fill in missing data for 零跑B10 (2026 facelift model)."""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from database import update_vehicle, insert_specs, get_vehicle_by_name
from image_manager import ImageManager
from data_collector import DataCollector


def update_b10_data():
    """Update 零跑B10 with complete 2026 facelift data."""
    
    vehicle = get_vehicle_by_name('零跑B10')
    if not vehicle:
        print("❌ 零跑B10 not found in database")
        return
    
    vehicle_id = vehicle['id']
    print(f"✅ Found 零跑B10, ID: {vehicle_id}")
    
    # Update vehicle basic info
    update_vehicle(
        vehicle_id,
        segment='紧凑型SUV',
        body_type='SUV',
        power_type='纯电',
        platform='LEAP3.5',
        status='预售',
        announce_date='2026-05-15',
        launch_date='2026-07-15',  # Estimated based on official pic release 7/3
        length=4515,
        width=1885,
        height=1655,
        wheelbase=2735,
        tags='激光雷达,8650芯片,LEAP3.5架构,后驱'
    )
    print("✅ Updated vehicle basic info")
    
    # Insert/Update specs
    insert_specs(
        vehicle_id=vehicle_id,
        motor_type='单电机',
        motor_power='185kW/132kW',
        motor_torque='350N·m/240N·m',
        battery_capacity='56.2/67.1',
        battery_brand='国轩高科/欣旺达',
        battery_type='磷酸铁锂',
        range_cltc='510/600',
        charging_time='19-26分钟(30%-80%)',
        drivetrain='后驱',
        suspension_front='麦弗逊',
        suspension_rear='多连杆',
        adas_level='L2+',
        chip='高通骁龙8650',
        radar='禾赛128线激光雷达'
    )
    print("✅ Updated specs")
    
    # Download new official images from the article
    # Note: In production this would be automated, for now we add URLs
    print("\n📝 备注：新款官图已发布，需要补充图片URL后自动下载")
    print("   数据来源：2026年7月3日零跑官方设计平台")
    
    print("\n✅ 零跑B10数据补全完成！")


if __name__ == '__main__':
    update_b10_data()
