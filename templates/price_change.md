**价格变化（Price）**

{% for item in price_changes %}
💰 **{{ item.name }}**
  {% if item.old_price %}- 原{{ item.price_type }}：{{ item.old_price }}万{% endif %}
  {% if item.new_price %}- {{ item.new_type }}：{{ item.new_price }}万{% endif %}
  {% if item.change %}- 变化：{{ item.change }}{% endif %}
  - 观点：{{ item.review }}

{% endfor %}
{% if not price_changes %}今日暂无价格变动。{% endif %}
