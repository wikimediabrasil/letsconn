from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')  # Return an empty string if the key is missing

@register.filter
def underscore(value):
    """Replace underscores with spaces."""
    return value.replace('_', ' ')