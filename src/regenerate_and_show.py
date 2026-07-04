"""Regenerate article and show result."""
import os
import shutil
from exporter import ArticleExporter

# Clean old export
export_dir = '../data/export/20260704'
if os.path.exists(export_dir):
    shutil.rmtree(export_dir)

# Export
exporter = ArticleExporter()
output = exporter.export_article()

# Show result
with open(output) as f:
    content = f.read()

print("=" * 60)
print(" regenerated article ".center(60, "="))
print("=" * 60)
print(content)
print("=" * 60)
print(f"Image refs: {content.count('![')}")
print(f"Has 零跑B10: {'零跑B10' in content}")
