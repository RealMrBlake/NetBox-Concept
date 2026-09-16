"""
Populate a planned device's components from its device type's templates - interfaces,
ports, and the front/rear pass-through mapping - so a concept device with a device type
can be cabled exactly like a real one. A device type's own component templates are the
single source of truth here; nothing about this is specific to any particular role, so
a "Patchpanel"-role device gets correct front/rear pass-through behaviour simply because
that's what its device type's templates already describe - the same as a real device.

Placeholder devices without a device type have no templates to sync from; their
components, if any, have to be added by hand.
"""
from django.db import transaction

from .choices import ConceptComponentTypeChoices
from .models import ConceptComponent, ConceptPortMapping

__all__ = ('sync_components',)

# (our component type, DeviceType's reverse accessor for that template queryset)
TEMPLATE_SOURCES = (
    (ConceptComponentTypeChoices.TYPE_INTERFACE, 'interfacetemplates'),
    (ConceptComponentTypeChoices.TYPE_CONSOLE_PORT, 'consoleporttemplates'),
    (ConceptComponentTypeChoices.TYPE_CONSOLE_SERVER_PORT, 'consoleserverporttemplates'),
    (ConceptComponentTypeChoices.TYPE_POWER_PORT, 'powerporttemplates'),
    (ConceptComponentTypeChoices.TYPE_POWER_OUTLET, 'poweroutlettemplates'),
    (ConceptComponentTypeChoices.TYPE_FRONT_PORT, 'frontporttemplates'),
    (ConceptComponentTypeChoices.TYPE_REAR_PORT, 'rearporttemplates'),
)


@transaction.atomic
def sync_components(concept_device):
    """
    Create whichever of the device type's components don't already exist on this
    device (matched by name), and mirror its front/rear port mapping. Existing
    components - and any cables already attached to them - are left untouched, so this
    is safe to re-run after adding extra components by hand or after the device type
    changes. Returns (components_created, mappings_created).
    """
    device_type = concept_device.device_type
    if device_type is None:
        return 0, 0

    existing = {component.name: component for component in concept_device.components.all()}
    created = 0

    for component_type, accessor in TEMPLATE_SOURCES:
        for template in getattr(device_type, accessor).all():
            if template.name in existing:
                continue
            component = ConceptComponent.objects.create(
                device=concept_device,
                component_type=component_type,
                name=template.name,
                label=template.label,
                port_type=getattr(template, 'type', '') or '',
                positions=getattr(template, 'positions', 1) or 1,
                color=getattr(template, 'color', '') or '',
            )
            existing[component.name] = component
            created += 1

    mappings_created = 0
    for mapping in device_type.port_mappings.select_related('front_port', 'rear_port').all():
        front = existing.get(mapping.front_port.name)
        rear = existing.get(mapping.rear_port.name)
        if not (front and rear):
            # Shouldn't happen - the templates were just synced above - but a
            # partially-synced device from before a device type change could hit this.
            continue
        _, was_created = ConceptPortMapping.objects.get_or_create(
            front_component=front,
            front_position=mapping.front_port_position,
            defaults={'rear_component': rear, 'rear_position': mapping.rear_port_position}
        )
        if was_created:
            mappings_created += 1

    return created, mappings_created
