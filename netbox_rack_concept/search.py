from netbox.search import SearchIndex, register_search

from .models import ConceptDevice, RackConcept


@register_search
class RackConceptIndex(SearchIndex):
    model = RackConcept
    fields = (
        ('name', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('status', 'tenant', 'description')


@register_search
class ConceptDeviceIndex(SearchIndex):
    model = ConceptDevice
    fields = (
        ('name', 100),
        ('label', 110),
        ('serial', 120),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('concept', 'status', 'device_type', 'role', 'description')
