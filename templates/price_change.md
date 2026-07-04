**价格变化（Price）**

{% for item in price_changes %}
💰 **{{ item.name }}**
  {% if item.old_price %}- 原来：{{ item.old_price }}万{% endif %}
  {% if item.new_price %}- 现在：{{ item.new_price }}万{% endif %}
  {% if item.change %}- 变化：{{ item.change }}{% endif %}
  - 老图算账：{{ item.review }}

{% endfor %}
{% if not price_changes %}今日暂无价格变动。{% endif %}
