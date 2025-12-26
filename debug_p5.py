import os
import sys

sys.path.append(os.getcwd())

from bengal.rendering.kida import Environment

env = Environment()
tmpl_str = """
{% macro factorial(n) %}
  DEBUG: n={{ n }}
  {% if n <= 1 %}
    1
  {% else %}
    {% set prev = factorial(n - 1) %}
    DEBUG: prev='{{ prev }}' (type={{ prev.__class__.__name__ }})
    {{ n * prev|int }}
  {% endif %}
{% endmacro %}
{{ factorial(3) }}
"""
try:
    res = env.from_string(tmpl_str).render()
    print(res)
except Exception as e:
    print(f"Error: {e}")
