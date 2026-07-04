**新车日历（Calendar）**

📅 **本周上市**
{% for car in this_week %}
○ {{ car.name }}（{{ car.date }}）{% if car.is_confirmed %}✓ 已确认{% else %}⏳ 预计{% endif %}
{% endfor %}
{% if not this_week %}（本周暂无新车上市）{% endif %}

📅 **本月上市**
{% for car in this_month %}
○ {{ car.name }}（{{ car.date }}）
{% endfor %}
{% if not this_month %}（本月暂无其他新车上市）{% endif %}

📅 **下月关注**
{% for car in next_month %}
○ {{ car.name }}（{{ car.date }}）
{% endfor %}
{% if not next_month %}（下月暂无预告车型）{% endif %}
