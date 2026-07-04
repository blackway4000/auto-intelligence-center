"""Image Manager: unified image storage, processing, and retrieval.

Storage structure:
  data/images/{brand}/{vehicle}/
    raw/       - downloaded original images
    clean/     - processed images (watermark removed)
    manifest.json - image metadata
"""

import os
import json
import hashlib
import requests
from typing import List, Dict, Optional, Tuple
from PIL import Image

BASE_IMAGE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'images')


class ImageManager:
    """Manage images organized by brand and vehicle."""
    
    def __init__(self, base_dir: str = BASE_IMAGE_DIR):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def _sanitize(self, name: str) -> str:
        """Sanitize directory name."""
        return name.replace('/', '-').replace('\\', '-').replace(' ', '_')
    
    def get_vehicle_dir(self, brand: str, vehicle: str) -> str:
        """Get image directory for a specific vehicle."""
        path = os.path.join(self.base_dir, self._sanitize(brand), self._sanitize(vehicle))
        os.makedirs(os.path.join(path, 'raw'), exist_ok=True)
        os.makedirs(os.path.join(path, 'clean'), exist_ok=True)
        return path
    
    def download_image(self, url: str, save_path: str, referer: str = None) -> bool:
        """Download a single image."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            }
            if referer:
                headers['Referer'] = referer
            
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            
            return True
        except Exception as e:
            print(f"  Download failed: {e}")
            return False
    
    def download_vehicle_images(self, brand: str, vehicle: str,
                                 image_urls: List[Dict],
                                 referer: str = None,
                                 max_images: int = 10) -> List[Dict]:
        """Download images for a vehicle.
        
        Args:
            image_urls: List of dicts with 'url' and optionally 'alt', 'source_type'
            max_images: Maximum number of images to download
        
        Returns:
            List of downloaded image metadata
        """
        vehicle_dir = self.get_vehicle_dir(brand, vehicle)
        raw_dir = os.path.join(vehicle_dir, 'raw')
        
        results = []
        
        for i, img_info in enumerate(image_urls[:max_images]):
            url = img_info.get('url') or img_info.get('src')
            if not url:
                continue
            
            # Determine extension
            ext = url.split('.')[-1].split('?')[0][:4].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                ext = 'jpg'
            
            filename = f"{i:02d}_{hashlib.md5(url.encode()).hexdigest()[:8]}.{ext}"
            raw_path = os.path.join(raw_dir, filename)
            
            # Skip if already downloaded
            if os.path.exists(raw_path):
                results.append({
                    'url': url,
                    'raw_path': raw_path,
                    'alt': img_info.get('alt', ''),
                    'source_type': img_info.get('source_type', 'unknown'),
                    'status': 'existing',
                })
                continue
            
            print(f"  [{i+1}/{min(len(image_urls), max_images)}] Downloading...")
            if self.download_image(url, raw_path, referer):
                results.append({
                    'url': url,
                    'raw_path': raw_path,
                    'alt': img_info.get('alt', ''),
                    'source_type': img_info.get('source_type', 'unknown'),
                    'status': 'downloaded',
                })
        
        # Save manifest
        manifest_path = os.path.join(vehicle_dir, 'manifest.json')
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        return results
    
    def process_images(self, brand: str, vehicle: str,
                       crop_bottom: int = 40) -> List[Dict]:
        """Process downloaded images (remove watermarks).
        
        Returns:
            List of processed image metadata
        """
        vehicle_dir = self.get_vehicle_dir(brand, vehicle)
        raw_dir = os.path.join(vehicle_dir, 'raw')
        clean_dir = os.path.join(vehicle_dir, 'clean')
        
        results = []
        
        for filename in sorted(os.listdir(raw_dir)):
            raw_path = os.path.join(raw_dir, filename)
            clean_path = os.path.join(clean_dir, filename)
            
            if os.path.exists(clean_path):
                results.append({
                    'raw': raw_path,
                    'clean': clean_path,
                    'status': 'existing',
                })
                continue
            
            try:
                img = Image.open(raw_path)
                width, height = img.size
                
                # Skip small images (icons, thumbnails)
                if width < 400 or height < 300:
                    continue
                
                # Crop bottom edge to remove watermark
                if height > crop_bottom * 3:
                    cropped = img.crop((0, 0, width, height - crop_bottom))
                    cropped.save(clean_path, quality=95)
                else:
                    img.save(clean_path, quality=95)
                
                results.append({
                    'raw': raw_path,
                    'clean': clean_path,
                    'status': 'processed',
                })
                print(f"  Processed: {filename}")
                
            except Exception as e:
                print(f"  Processing failed {filename}: {e}")
        
        return results
    
    def get_image_paths(self, brand: str, vehicle: str,
                        max_count: int = 5,
                        prefer_clean: bool = True) -> List[str]:
        """Get image paths for content generation.
        
        Returns:
            List of image file paths
        """
        vehicle_dir = self.get_vehicle_dir(brand, vehicle)
        
        if prefer_clean:
            img_dir = os.path.join(vehicle_dir, 'clean')
        else:
            img_dir = os.path.join(vehicle_dir, 'raw')
        
        if not os.path.exists(img_dir):
            return []
        
        # Get all valid image files
        valid_exts = ('.jpg', '.jpeg', '.png', '.webp')
        images = [
            os.path.join(img_dir, f)
            for f in sorted(os.listdir(img_dir))
            if f.lower().endswith(valid_exts)
        ]
        
        return images[:max_count]
    
    def copy_for_export(self, brand: str, vehicle: str,
                        export_dir: str, max_count: int = 5,
                        start_index: int = 1) -> List[str]:
        """Copy images to export directory for article publishing.
        
        Args:
            start_index: Global index offset to avoid filename collisions
                         when multiple vehicles share the same export dir.
        
        Returns:
            List of relative paths for markdown reference
        """
        import shutil
        
        source_paths = self.get_image_paths(brand, vehicle, max_count)
        if not source_paths:
            return []
        
        export_img_dir = os.path.join(export_dir, 'images')
        os.makedirs(export_img_dir, exist_ok=True)
        
        result_paths = []
        for i, src_path in enumerate(source_paths):
            ext = os.path.splitext(src_path)[1]
            dest_name = f"img_{start_index + i:02d}{ext}"
            dest_path = os.path.join(export_img_dir, dest_name)
            shutil.copy2(src_path, dest_path)
            result_paths.append(f"images/{dest_name}")
        
        return result_paths
    
    def list_vehicle_images(self, brand: str, vehicle: str) -> Dict:
        """List all images for a vehicle."""
        vehicle_dir = self.get_vehicle_dir(brand, vehicle)
        
        raw_images = []
        clean_images = []
        
        raw_dir = os.path.join(vehicle_dir, 'raw')
        clean_dir = os.path.join(vehicle_dir, 'clean')
        
        if os.path.exists(raw_dir):
            raw_images = [f for f in os.listdir(raw_dir) if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        
        if os.path.exists(clean_dir):
            clean_images = [f for f in os.listdir(clean_dir) if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        
        return {
            'brand': brand,
            'vehicle': vehicle,
            'raw_count': len(raw_images),
            'clean_count': len(clean_images),
            'raw_dir': raw_dir,
            'clean_dir': clean_dir,
        }


if __name__ == '__main__':
    # Test
    manager = ImageManager()
    
    # List existing images
    print("=" * 60)
    print("图片管理器测试")
    print("=" * 60)
    
    # Test with existing data
    result = manager.list_vehicle_images('零跑汽车', 'leapmotor')
    print(f"\n零跑汽车: raw={result['raw_count']}, clean={result['clean_count']}")
    
    # Test getting paths
    paths = manager.get_image_paths('零跑汽车', 'leapmotor', max_count=3)
    print(f"可用图片: {len(paths)}")
    for p in paths:
        print(f"  - {p}")
