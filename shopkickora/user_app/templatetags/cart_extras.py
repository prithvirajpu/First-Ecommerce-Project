from django import template
from decimal import Decimal


register = template.Library()

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except:
        return ''
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

