from django import template

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

@register.filter
def split(value, delimiter=","):
    return value.split(delimiter)

@register.filter
def to(value, end):
    return range(value, end)

@register.filter
def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

@register.filter
def index_of(value_list, target):
    try:
        return value_list.index(target)
    except ValueError:
        return -1