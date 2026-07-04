"""Test full pipeline: collect → generate → export with images."""

from exporter import ArticleExporter
import os

exporter = ArticleExporter()
output = exporter.export_article()

if output:
    with open(output) as f:
        content = f.read()
    
    print("=" * 60)
    print("完整推文测试")
    print("=" * 60)
    print(f"\n导出路径: {output}")
    print(f"包含图片引用: {'![' in content}")
    
    # Check exported images
    export_dir = os.path.dirname(output)
    img_dir = os.path.join(export_dir, 'images')
    if os.path.exists(img_dir):
        files = os.listdir(img_dir)
        print(f"导出图片数: {len(files)}")
        for f in files:
            print(f"  - {f}")
    
    print("\n--- 推文内容预览 ---")
    print(content[:1200])
    print("\n...")
else:
    print("导出失败")
