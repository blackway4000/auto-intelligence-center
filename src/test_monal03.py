"""Test content generation with real Xiaopeng MONA L03 data."""

from ai_generator import ContentGenerator

generator = ContentGenerator()

# Real data from benchmark article analysis
mona_l03 = {
    'id': 101,
    'name': '小鹏MONA L03',
    'brand_id': 5,
    'segment': '紧凑型SUV',
    'power_type': '纯电/增程',
    'status': '预售',
    'presale_date': '2026-07-02',
    'launch_date': '2026-07-15',
    'tags': '图灵芯片,249Ps后驱,前麦弗逊后多连杆',
    'min_price': 14.38,
    'max_price': 16.18,
}

results = generator.generate_all([mona_l03])

print("=" * 60)
print("【模拟推文】小鹏MONA L03 预售发布")
print("=" * 60)

# Combine all sections into one article
article = f"""
{results['daily']}

{results['calendar']}

{results['price']}

{results['review']}
"""

print(article)

print("\n" + "=" * 60)
print("【对比：接入规则引擎后的提升】")
print("=" * 60)
print("""
改进前（模板填充）：
  - 一句话辣评：新车型动态更新  ← 固定文案
  - 核心看点：图灵芯片,249Ps后驱,前麦弗逊后多连杆  ← 直接拿tags
  - 适合谁：待定  ← 不会判断
  - 咆哮哥拍板：★★★★☆ 值得关注  ← 固定文案
  - 没有开头情绪

改进后（规则引擎）：
  - 一句话辣评：根据价格+配置自动生成（如"配置拉满，诚意够狠"）
  - 核心看点：tags自动翻译为人话（如"智驾芯片强、后驱有驾驶感、底盘舒适"）
  - 适合谁：根据级别+价格+动力自动判断（如"预算15万、想要第一台车的年轻人"）
  - 咆哮哥拍板：根据性价比自动判断（如"★★★★☆ 能买，但等正式上市再看有没有惊喜"）
  - 开头情绪：随机生成"一觉醒来..."或"真的服了..."
  - 版本建议：根据智驾配置推荐中配
""")
