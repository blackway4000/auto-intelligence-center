**咆哮哥点评**

{% for car in vehicles %}
{{ car.name }}：{{ car.rating }}
{{ car.review }}

{% endfor %}
{% if not vehicles %}暂无车型点评。{% endif %}
