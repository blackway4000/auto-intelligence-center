"""Export complete article with images for publishing.

Usage:
    from exporter import ArticleExporter
    exporter = ArticleExporter()
    exporter.export_article(vehicle_ids=[1, 2], output_dir='data/export/20260704')
"""

import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional

from database import list_vehicles, get_connection
from ai_generator import ContentGenerator
from image_manager import ImageManager


class ArticleExporter:
    """Export complete article with all columns and images."""
    
    def __init__(self):
        self.generator = ContentGenerator()
        self.image_manager = ImageManager()
    
    def export_article(self, vehicle_ids: Optional[List[int]] = None,
                       output_dir: Optional[str] = None,
                       date_str: Optional[str] = None) -> str:
        """Export a complete article.
        
        Args:
            vehicle_ids: Specific vehicle IDs to include, or None for all recent vehicles
            output_dir: Custom output directory, or auto-generated from date
            date_str: Date string for directory naming (default: today)
        
        Returns:
            Path to exported article markdown file
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(__file__), '..', 'data', 'export', date_str
            )
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Get vehicles
        if vehicle_ids:
            vehicles = self._get_vehicles_by_ids(vehicle_ids)
        else:
            vehicles = list_vehicles(status='预售')[:5]
            if not vehicles:
                vehicles = list_vehicles()[:5]
        
        if not vehicles:
            print("No vehicles to export")
            return ""
        
        # Step 1: Copy images and update vehicle dict with export-relative paths
        print("收集图片...")
        image_refs = []
        img_index = 1  # Global index to avoid filename collisions across vehicles
        for v in vehicles:
            brand = self._get_brand_name(v['brand_id'])
            vehicle_name = v['name']
            
            # Copy images to export dir, get relative paths like images/img_01.jpg
            copied = self.image_manager.copy_for_export(
                brand, vehicle_name, output_dir, max_count=3, start_index=img_index
            )
            image_refs.extend(copied)
            
            # Update vehicle dict so generator uses export-relative paths
            if copied:
                v['image_urls'] = copied
                img_index += len(copied)
        
        # Step 2: Generate content (now with correct image paths)
        print(f"\n生成内容 ({len(vehicles)} 款车型)...")
        results = self.generator.generate_all(vehicles)
        
        # Build article
        article = self._build_article(results, vehicles, image_refs)
        
        # Write to file
        output_path = os.path.join(output_dir, 'article.md')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(article)
        
        print(f"\n✅ 推文已导出: {output_path}")
        print(f"   图片: {len(image_refs)} 张")
        print(f"   车型: {len(vehicles)} 款")
        
        return output_path
    
    def _get_vehicles_by_ids(self, vehicle_ids: List[int]) -> List[Dict]:
        """Get vehicles by IDs."""
        conn = get_connection()
        conn.row_factory = lambda c, r: {col[0]: r[idx] for idx, col in enumerate(c.description)}
        cursor = conn.cursor()
        
        placeholders = ', '.join(['?'] * len(vehicle_ids))
        cursor.execute(f"""
            SELECT v.*, b.name as brand_name
            FROM vehicles v
            JOIN brands b ON v.brand_id = b.id
            WHERE v.id IN ({placeholders})
        """, vehicle_ids)
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def _get_brand_name(self, brand_id: int) -> str:
        """Get brand name by ID."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM brands WHERE id = ?", (brand_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 'Unknown'
    
    def _build_article(self, results: Dict[str, str], vehicles: List[Dict],
                       image_refs: List[str]) -> str:
        """Build complete article markdown."""
        date_str = datetime.now().strftime('%Y年%m月%d日')
        
        # Header
        lines = [
            f"# 新车日报 | {date_str}",
            "",
            "---",
            "",
        ]
        
        # Daily new cars
        lines.extend([
            results['daily'],
            "",
            "---",
            "",
        ])
        
        # Calendar
        lines.extend([
            results['calendar'],
            "",
            "---",
            "",
        ])
        
        # Price changes
        lines.extend([
            results['price'],
            "",
            "---",
            "",
        ])
        
        # Reviews
        lines.extend([
            results['review'],
            "",
            "---",
            "",
        ])
        
        # Footer
        lines.extend([
            "*以上信息基于公开数据整理，具体以官方公布为准。*",
            "",
        ])
        
        return '\n'.join(lines)


if __name__ == '__main__':
    # Test export
    exporter = ArticleExporter()
    
    # Export all recent vehicles
    output = exporter.export_article()
    
    if output:
        print(f"\n{'='*60}")
        print("推文预览（前500字）")
        print('='*60)
        with open(output, 'r') as f:
            preview = f.read()[:500]
            print(preview)
            print("...")
