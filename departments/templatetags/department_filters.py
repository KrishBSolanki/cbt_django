"""
Department template filters
"""
from django import template

register = template.Library()


@register.filter
def split(value, arg):
    """
    Split a string by the given delimiter.
    Usage: {{ "a,b,c"|split:"," }}
    """
    return value.split(arg)
