from netbox.search import SearchIndex, register_search

from .models import ConceptCable, ConceptComponent, ConceptDevice, RackConcept


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


@register_search
class ConceptComponentIndex(SearchIndex):
    model = ConceptComponent
    fields = (
        ('name', 100),
        ('label', 110),
        ('description', 500),
    )
    display_attrs = ('device', 'component_type', 'port_type')


@register_search
class ConceptCableIndex(SearchIndex):
    model = ConceptCable
    fields = (
        ('label', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('status', 'type', 'description')
