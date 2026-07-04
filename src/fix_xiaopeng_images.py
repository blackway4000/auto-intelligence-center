"""Download Xpeng MONA L03 images and update database.

Extracted image URLs from xiaopeng.com homepage.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from image_manager import ImageManager
from database import get_vehicle_by_name, update_vehicle, get_connection
import json

# Image URLs extracted from xiaopeng.com homepage (high-res vehicle banners)
# These are official brand images, suitable for publication
MONA_L03_IMAGES = [
    {'url': 'https://xps01.xiaopeng.com/cms/material/pic/2026/07-01/pic_20260701120539_31837.jpg', 'alt': 'MONA L03 banner'},
    {'url': 'https://xps01.xiaopeng.com/cms/material/pic/2026/05-15/pic_20260515174350_96159.jpg', 'alt': 'MONA L03 exterior'},
    {'url': 'https://xps01.xiaopeng.com/cms/material/pic/2026/06-04/pic_20260604103956_50230.jpg', 'alt': 'MONA L03 detail'},
]


def download_and_update():
    """Download images and update vehicle record."""
    manager = ImageManager()
    
    print("=" * 60)
    print("给小鹏MONA L03补充官方图片")
    print("=" * 60)
    
    # Check vehicle exists
    vehicle = get_vehicle_by_name('小鹏MONA L03')
    if not vehicle:
        print("❌ 数据库中没有找到 小鹏MONA L03")
        return
    
    vehicle_id = vehicle['id']
    print(f"✅ 找到车型，ID: {vehicle_id}")
    
    # Download images
    print(f"\n下载 {len(MONA_L03_IMAGES)} 张官方图片...")
    downloaded = manager.download_vehicle_images(
        brand='小鹏汽车',
        vehicle='小鹏MONA L03',
        image_urls=MONA_L03_IMAGES,
        referer='https://www.xiaopeng.com',
        max_images=5
    )
    
    success_count = len([d for d in downloaded if d['status'] in ('downloaded', 'existing')])
    print(f"✅ 成功下载 {success_count} 张")
    
    # Process images (crop watermark)
    print("\n处理图片（去水印）...")
    processed = manager.process_images('小鹏汽车', '小鹏MONA L03')
    print(f"✅ 成功处理 {len(processed)} 张")
    
    # Get clean paths and update database
    image_paths = manager.get_image_paths('小鹏汽车', '小鹏MONA L03', max_count=10)
    if image_paths:
        update_vehicle(vehicle_id, image_urls=json.dumps(image_paths))
        print(f"\n✅ 已更新数据库，image_urls: {len(image_paths)} 张")
        for p in image_paths:
            print(f"   - {p}")
    else:
        print("⚠️ 没有可用图片路径")
    
    print("\n" + "=" * 60)
    print("完成！现在可以运行 exporter.py 导出完整推文")
    print("=" * 60)


if __name__ == '__main__':
    download_and_update()
