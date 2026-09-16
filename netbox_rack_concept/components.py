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
from django.core.exceptions import ValidationError
from django.db import transaction

from dcim.models import Cable, ConsolePort, ConsoleServerPort, FrontPort, Interface, PowerOutlet, PowerPort, RearPort

from .choices import ConceptComponentTypeChoices
from .models import ConceptCable, ConceptComponent, ConceptPortMapping

__all__ = ('copy_cables', 'sync_components')

# (our component type, the real dcim model that can terminate a real cable)
CABLED_MODELS = (
    (ConceptComponentTypeChoices.TYPE_INTERFACE, Interface),
    (ConceptComponentTypeChoices.TYPE_CONSOLE_PORT, ConsolePort),
    (ConceptComponentTypeChoices.TYPE_CONSOLE_SERVER_PORT, ConsoleServerPort),
    (ConceptComponentTypeChoices.TYPE_POWER_PORT, PowerPort),
    (ConceptComponentTypeChoices.TYPE_POWER_OUTLET, PowerOutlet),
    (ConceptComponentTypeChoices.TYPE_FRONT_PORT, FrontPort),
    (ConceptComponentTypeChoices.TYPE_REAR_PORT, RearPort),
)

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


@transaction.atomic
def copy_cables(concept_devices):
    """
    Recreate, as ConceptCables, every real cable whose both ends sit on one of the
    given concept devices' source devices (i.e. cables internal to whatever rack(s)
    were just imported). A cable reaching a device outside that set can't be
    represented here - the other end isn't part of the concept - and is skipped, along
    with any multi-termination trunk cable, which ConceptCable's plain point-to-point
    model can't hold. Only devices whose components have already been synced (see
    sync_components) can have their cables copied.
    Returns (copied, skipped).
    """
    device_map = {cd.source_device_id: cd for cd in concept_devices if cd.source_device_id}
    if not device_map:
        return 0, 0
    device_ids = set(device_map)

    component_lookup = {}
    for component in ConceptComponent.objects.filter(device__in=device_map.values()).select_related('device'):
        component_lookup[(component.device.source_device_id, component.name)] = component

    cable_ids = set()
    for _, model in CABLED_MODELS:
        cable_ids.update(
            model.objects.filter(device_id__in=device_ids, cable_id__isnull=False)
            .values_list('cable_id', flat=True)
        )

    copied = skipped = 0
    for cable in Cable.objects.filter(pk__in=cable_ids).prefetch_related('terminations'):
        a_ends = [ct.termination for ct in cable.terminations.all() if ct.cable_end == 'A']
        b_ends = [ct.termination for ct in cable.terminations.all() if ct.cable_end == 'B']
        if len(a_ends) != 1 or len(b_ends) != 1:
            # A multi-termination trunk cable - not something a point-to-point
            # ConceptCable can represent.
            skipped += 1
            continue

        a, b = a_ends[0], b_ends[0]
        a_device_id, b_device_id = getattr(a, 'device_id', None), getattr(b, 'device_id', None)
        if a_device_id not in device_ids or b_device_id not in device_ids:
            # Reaches a device outside the set being copied.
            skipped += 1
            continue

        component_a = component_lookup.get((a_device_id, a.name))
        component_b = component_lookup.get((b_device_id, b.name))
        if not (component_a and component_b):
            skipped += 1
            continue

        concept_cable = ConceptCable(
            termination_a=component_a,
            termination_b=component_b,
            status=cable.status,
            type=cable.type or '',
            color=cable.color or '',
            label=cable.label,
        )
        try:
            concept_cable.full_clean()
        except ValidationError:
            skipped += 1
            continue
        concept_cable.save()
        copied += 1

    return copied, skipped
