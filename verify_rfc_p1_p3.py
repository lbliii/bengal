import os
import sys

# Add the root directory to sys.path
sys.path.append(os.getcwd())


from bengal.rendering.kida import Environment

env = Environment()

print("P1: Unmatched End Tags")
try:
    res = env.from_string("{% endif %}").render()
    print(f"  Result: '{res}' (Silent Success)")
except Exception as e:
    print(f"  Error: {e}")

print("\nP2: Missing End Tags")
try:
    res = env.from_string("{% if true %}content").render()
    print(f"  Result: '{res}' (Silent Success)")
except Exception as e:
    print(f"  Error: {e}")

print("\nP3: Mismatched Block Tags")
try:
    res = env.from_string("{% if true %}{% endfor %}").render()
    print(f"  Result: '{res}' (Silent Success)")
except Exception as e:
    print(f"  Error: {e}")

print("\nP4: Invalid Operators (Testing 2 ** 3)")
try:
    res = env.from_string("{{ 2 ** 3 }}").render()
    print(f"  Result: '{res}' (Should be 8 if supported)")
except Exception as e:
    print(f"  Error: {e}")

print("\nP5: Macro Recursion")
tmpl_str = """
{% macro factorial(n) %}
{% if n <= 1 %}1{% else %}{{ n * factorial(n - 1)|int }}{% endif %}
{% endmacro %}
{{ factorial(5) }}
"""
try:
    res = env.from_string(tmpl_str).render().strip()
    print(f"  Result: '{res}' (Should be '120')")
except Exception as e:
    print(f"  Error: {e}")
