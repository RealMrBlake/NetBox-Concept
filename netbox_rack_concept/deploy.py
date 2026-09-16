"""
The three copy paths: rack -> concept, concept -> concept, concept -> rack(s).
"""
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext as _

from dcim.models import Device, Rack

from .choices import ConceptDeviceStatusChoices, ConceptStatusChoices
from .integrations import apply_partial_width, read_partial_width
from .models import ConceptDeployment, ConceptDevice, RackConcept

__all__ = (
    'clone_concept',
    'copy_rack_to_concept',
    'deploy_concept',
    'validate_deployment',
)

GEOMETRY_FIELDS = (
    'form_factor', 'width', 'u_height', 'starting_unit', 'desc_units', 'outer_width', 'outer_height',
    'outer_depth', 'outer_unit', 'mounting_depth', 'airflow', 'max_weight',
)


def _config():
    return settings.PLUGINS_CONFIG.get('netbox_rack_concept', {})


#
# dcim.Rack -> RackConcept
#

@transaction.atomic
def copy_rack_to_concept(rack, name, status=ConceptStatusChoices.STATUS_DRAFT, tenant=None, tenant_group=None,
                         description='', include_devices=True, include_device_names=True):
    """Snapshot a real rack, and optionally its contents, into a new blueprint."""
    concept = RackConcept(
        name=name,
        status=status,
        tenant=tenant,
        tenant_group=tenant_group,
        description=description,
        rack_type=rack.rack_type,
        default_site=rack.site,
        default_location=rack.location,
        rack_role=rack.role,
        source_rack=rack,
    )
    for field in GEOMETRY_FIELDS:
        value = getattr(rack, field, None)
        # A rack built from a rack type may leave its own dimension fields empty.
        if value in (None, '') and rack.rack_type:
            value = getattr(rack.rack_type, field, None)
        if value not in (None, ''):
            setattr(concept, field, value)
    concept.full_clean()
    concept.save()

    if include_devices:
        devices = Device.objects.filter(rack=rack, position__isnull=False).select_related(
            'device_type', 'role', 'platform', 'tenant'
        )
        for device in devices:
            fraction, horizontal = read_partial_width(device)
            ConceptDevice.objects.create(
                concept=concept,
                name=(device.name or '') if include_device_names else '',
                status=ConceptDeviceStatusChoices.STATUS_EXISTING,
                device_type=device.device_type,
                role=device.role,
                platform=device.platform,
                tenant=device.tenant,
                position=device.position,
                face=device.face,
                width_fraction=fraction,
                horizontal_position=horizontal,
                serial=device.serial if include_device_names else '',
                source_device=device,
            )

    return concept


#
# RackConcept -> RackConcept
#

@transaction.atomic
def clone_concept(concept, name, status=ConceptStatusChoices.STATUS_DRAFT, tenant=None, include_devices=True):
    """Duplicate a blueprint so variants can be built without touching the original."""
    clone = RackConcept(
        name=name,
        status=status,
        tenant=tenant or concept.tenant,
        tenant_group=concept.tenant_group,
        description=concept.description,
        comments=concept.comments,
        rack_type=concept.rack_type,
        default_site=concept.default_site,
        default_location=concept.default_location,
        rack_role=concept.rack_role,
        source_rack=concept.source_rack,
    )
    for field in GEOMETRY_FIELDS:
        setattr(clone, field, getattr(concept, field))
    clone.full_clean()
    clone.save()

    if include_devices:
        for device in concept.devices.all():
            ConceptDevice.objects.create(
                concept=clone,
                name=device.name,
                label=device.label,
                status=device.status,
                device_type=device.device_type,
                role=device.role,
                platform=device.platform,
                tenant=device.tenant,
                position=device.position,
                face=device.face,
                width_fraction=device.width_fraction,
                horizontal_position=device.horizontal_position,
                u_height=device.u_height,
                is_full_depth=device.is_full_depth,
                serial=device.serial,
                description=device.description,
                comments=device.comments,
                source_device=device.source_device,
            )

    return clone


#
# RackConcept -> dcim.Rack
#

def validate_deployment(concept, create_devices=True, skip_unnamed_devices=True):
    """
    Report what a deployment would and would not be able to create. Returned as
    (deployable_devices, warnings) so the confirmation page can show it before anything
    is written.
    """
    warnings = []
    deployable = []

    if create_devices:
        for device in concept.devices.select_related('device_type', 'role'):
            if device.position is None:
                warnings.append(_('%(device)s has no position and will not be created.') % {'device': device})
                continue
            if device.device_type is None:
                warnings.append(
                    _('%(device)s is reserved space without a device type and will not be created.')
                    % {'device': device}
                )
                continue
            if device.role is None:
                warnings.append(
                    _('%(device)s has no role. NetBox requires one, so it will not be created.')
                    % {'device': device}
                )
                continue
            if not device.name and skip_unnamed_devices:
                warnings.append(_('%(device)s has no name and will be skipped.') % {'device': device})
                continue
            if device.status == ConceptDeviceStatusChoices.STATUS_OPTIONAL:
                warnings.append(
                    _('%(device)s is marked optional but will be created.') % {'device': device}
                )
            deployable.append(device)

    return deployable, warnings


@transaction.atomic
def deploy_concept(concept, rack_names, site, location=None, tenant=None, create_devices=True,
                   device_name_pattern='', skip_unnamed_devices=True, user=None):
    """
    Materialise the blueprint as one real rack per name in `rack_names`.
    Returns (racks, devices, warnings).
    """
    config = _config()
    rack_status = config.get('deployed_rack_status', 'planned')
    device_status = config.get('deployed_device_status', 'planned')

    planned, warnings = validate_deployment(concept, create_devices, skip_unnamed_devices)

    racks = []
    created_devices = []

    for rack_name in rack_names:
        rack = Rack(
            name=rack_name,
            site=site,
            location=location,
            tenant=tenant or concept.tenant,
            status=rack_status,
            role=concept.rack_role,
            description=concept.description,
            comments=concept.comments,
        )
        if concept.rack_type:
            # Let NetBox derive the geometry from the rack type rather than fighting it.
            rack.rack_type = concept.rack_type
        else:
            for field in GEOMETRY_FIELDS:
                setattr(rack, field, getattr(concept, field))
        rack.full_clean()
        rack.save()
        racks.append(rack)

        rack_device_count = 0
        for planned_device in planned:
            name = planned_device.name
            if name and device_name_pattern:
                name = device_name_pattern.format(rack=rack_name, name=planned_device.name)

            device = Device(
                name=name or None,
                device_type=planned_device.device_type,
                role=planned_device.role,
                platform=planned_device.platform,
                site=site,
                location=location,
                rack=rack,
                position=planned_device.position,
                face=planned_device.face,
                status=device_status,
                tenant=planned_device.tenant or tenant or concept.tenant,
                serial=planned_device.serial,
                description=planned_device.description,
            )
            device.full_clean()
            device.save()
            apply_partial_width(device, planned_device)
            created_devices.append(device)
            rack_device_count += 1

        ConceptDeployment.objects.create(
            concept=concept,
            rack=rack,
            rack_name=rack_name,
            device_count=rack_device_count,
            user=user if user and user.is_authenticated else None,
        )

    return racks, created_devices, warnings
