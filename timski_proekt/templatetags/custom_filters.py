from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Врати вредност од речник со даден клуч.
    Пример во template: {{ dictionary|get_item:key }}
    """
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def dict_key(dictionary, key):
    """Алтернативна имплементација"""
    try:
        return dictionary[key]
    except (KeyError, TypeError):
        return None