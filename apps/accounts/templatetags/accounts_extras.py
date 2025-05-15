from django import template

register = template.Library()

@register.filter
def getitem(dictionary, key):
    """Filtre pour accéder aux éléments d'un dictionnaire dans un template"""
    return dictionary.get(key, '') 