from django import template

register = template.Library()
print("DEBUG: custom_filters.py loaded")

@register.filter
def replace(value, arg):
    """
    Usage: {{ value|replace:"_ " }}
    Note: Django filters only take one argument. 
    We can pass "_, " and split it.
    """
    if len(arg.split('|')) == 2:
        old, new = arg.split('|')
        return value.replace(old, new)
    return value.replace(arg, " ")
