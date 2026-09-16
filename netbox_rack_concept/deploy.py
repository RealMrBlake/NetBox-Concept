"""
The five copy paths: rack -> concept, concept -> concept, concept -> rack(s),
concept + concept -> one merged concept, and rack + rack -> one merged concept.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from dcim.choices import DeviceFaceChoices, RackWidthChoices
from dcim.models import Device, Rack

from . import components
from .choices import ConceptDeviceStatusChoices, ConceptStatusChoices
from .integrations import apply_partial_width, read_partial_width
from .models import ConceptDeployment, ConceptDevice, RackConcept

__all__ = (
    'clone_concept',
    'copy_rack_to_concept',
    'deploy_concept',
    'merge_concepts',
    'merge_racks_to_concept',
    'validate_deployment',
)

GEOMETRY_FIELDS = (
    'form_factor', 'width', 'u_height', 'starting_unit', 'desc_units', 'outer_width', 'outer_height',
    'outer_depth', 'outer_unit', 'mounting_depth', 'airflow', 'max_weight',
)


def _config():
    return settings.PLUGINS_CONFIG.get('netbox_rack_concept', {})


def _rack_geometry(rack, field):
    """A rack's own value for `field`, falling back to its rack type when left empty."""
    value = getattr(rack, field, None)
    if value in (None, '') and rack.rack_type:
        value = getattr(rack.rack_type, field, None)
    return value


#
# dcim.Rack -> RackConcept
#

@transaction.atomic
def copy_rack_to_concept(rack, name, status=ConceptStatusChoices.STATUS_DRAFT, tenant=None, tenant_group=None,
                         description='', include_devices=True, include_device_names=True,
                         override_width=None, override_u_height=None, override_starting_unit=None):
    """
    Snapshot a real rack, and optionally its contents, into a new blueprint. Passing an
    override lets the concept end up a different size than the source rack (e.g. to
    plan "what if we had a taller one"); devices that no longer fit are skipped and
    reported back as warnings rather than aborting the whole copy.

    Copied devices also get their components synced from their device type, and any
    cable between two of them is recreated as a ConceptCable - so the copy is cabled
    exactly like the source rack wherever both ends of a cable stayed inside it.
    Returns (concept, warnings, cable_summary), where cable_summary is
    {'copied': int, 'skipped': int}.
    """
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
        value = _rack_geometry(rack, field)
        if value not in (None, ''):
            setattr(concept, field, value)

    has_override = any(v is not None for v in (override_width, override_u_height, override_starting_unit))
    if has_override:
        # The concept's own geometry fields are ignored on deploy as long as rack_type
        # is set (NetBox derives geometry from the type). Since the override is the
        # whole point here, it must not be silently overruled by the source's type.
        concept.rack_type = None
    if override_width:
        concept.width = override_width
    if override_u_height:
        concept.u_height = override_u_height
    if override_starting_unit:
        concept.starting_unit = override_starting_unit

    concept.full_clean()
    concept.save()

    warnings = []
    cable_summary = {'copied': 0, 'skipped': 0}
    if include_devices:
        devices = Device.objects.filter(rack=rack, position__isnull=False).select_related(
            'device_type', 'role', 'platform', 'tenant'
        )
        new_devices = []
        for device in devices:
            fraction, horizontal = read_partial_width(device)
            concept_device = ConceptDevice(
                concept=concept,
                name=(device.name or '') if include_device_names else '',
                status=ConceptDeviceStatusChoices.STATUS_EXISTING,
                device_type=device.device_type,
                role=device.role,
                platform=device.platform,
                tenant=device.tenant,
                position=device.position,
                face=device.face or DeviceFaceChoices.FACE_FRONT,
                width_fraction=fraction,
                horizontal_position=horizontal,
                serial=device.serial if include_device_names else '',
                source_device=device,
            )
            if has_override:
                try:
                    concept_device.full_clean()
                except ValidationError:
                    warnings.append(_(
                        '%(device)s (U%(position)s) does not fit in the chosen size and was left out.'
                    ) % {'device': device, 'position': device.position})
                    continue
            concept_device.save()
            new_devices.append(concept_device)

        # Recreate each device's components from its device type, then wire up
        # whichever cables stayed entirely inside the rack being copied.
        for concept_device in new_devices:
            components.sync_components(concept_device)
        cable_summary['copied'], cable_summary['skipped'] = components.copy_cables(new_devices)

    return concept, warnings, cable_summary


#
# RackConcept + RackConcept -> RackConcept (stacked)
#

@transaction.atomic
def merge_concepts(concept_bottom, concept_top, name, status=ConceptStatusChoices.STATUS_DRAFT, tenant=None,
                   tenant_group=None, width=None, u_height=None, starting_unit=1, description=''):
    """
    Stack two blueprints into one taller one - e.g. two half-height racks combined into
    a full-height rack. concept_bottom's devices keep their position; concept_top's are
    shifted up by concept_bottom's height. Neither source concept is modified.
    Returns (merged_concept, warnings).
    """
    offset = concept_bottom.u_height
    total_height = u_height or (concept_bottom.u_height + concept_top.u_height)

    merged = RackConcept(
        name=name,
        status=status,
        tenant=tenant,
        tenant_group=tenant_group,
        description=description,
        width=width or concept_bottom.width,
        u_height=total_height,
        starting_unit=starting_unit,
        form_factor=concept_bottom.form_factor,
        airflow=concept_bottom.airflow,
        default_site=concept_bottom.default_site or concept_top.default_site,
        default_location=concept_bottom.default_location or concept_top.default_location,
        rack_role=concept_bottom.rack_role or concept_top.rack_role,
    )
    merged.full_clean()
    merged.save()

    warnings = []

    def _copy_devices(source, shift):
        for device in source.devices.all():
            concept_device = ConceptDevice(
                concept=merged,
                name=device.name,
                label=device.label,
                status=device.status,
                device_type=device.device_type,
                role=device.role,
                platform=device.platform,
                tenant=device.tenant,
                position=(device.position + shift) if device.position is not None else None,
                face=device.face or DeviceFaceChoices.FACE_FRONT,
                width_fraction=device.width_fraction,
                horizontal_position=device.horizontal_position,
                u_height=device.u_height,
                is_full_depth=device.is_full_depth,
                serial=device.serial,
                description=device.description,
                comments=device.comments,
                source_device=device.source_device,
            )
            try:
                concept_device.full_clean()
            except ValidationError:
                warnings.append(_(
                    '%(device)s from %(concept)s does not fit at its shifted position and was left out.'
                ) % {'device': device, 'concept': source})
                continue
            concept_device.save()

    _copy_devices(concept_bottom, 0)
    _copy_devices(concept_top, offset)

    return merged, warnings


#
# dcim.Rack + dcim.Rack -> RackConcept (stacked)
#

@transaction.atomic
def merge_racks_to_concept(rack_bottom, rack_top, name, status=ConceptStatusChoices.STATUS_DRAFT, tenant=None,
                           tenant_group=None, width=None, u_height=None, starting_unit=1, description='',
                           include_devices=True, include_device_names=True):
    """
    Combine two real racks directly into one new, taller blueprint - e.g. two
    half-height racks planned as one full-height rack. rack_bottom's devices keep their
    position; rack_top's are shifted up by rack_bottom's height. Neither source rack is
    modified.

    Copied devices also get their components synced from their device type, and any
    cable between two of them (from either rack) is recreated as a ConceptCable.
    Returns (concept, warnings, cable_summary), where cable_summary is
    {'copied': int, 'skipped': int}.
    """
    bottom_height = _rack_geometry(rack_bottom, 'u_height') or rack_bottom.u_height
    top_height = _rack_geometry(rack_top, 'u_height') or rack_top.u_height
    total_height = u_height or (bottom_height + top_height)

    concept = RackConcept(
        name=name,
        status=status,
        tenant=tenant,
        tenant_group=tenant_group,
        description=description,
        width=width or _rack_geometry(rack_bottom, 'width') or RackWidthChoices.WIDTH_19IN,
        u_height=total_height,
        starting_unit=starting_unit,
        form_factor=_rack_geometry(rack_bottom, 'form_factor') or '',
        airflow=rack_bottom.airflow or '',
        default_site=rack_bottom.site,
        default_location=rack_bottom.location,
        rack_role=rack_bottom.role,
        source_rack=rack_bottom,
    )
    concept.full_clean()
    concept.save()

    warnings = []
    new_devices = []

    def _copy_from_rack(rack, shift):
        if not include_devices:
            return
        devices = Device.objects.filter(rack=rack, position__isnull=False).select_related(
            'device_type', 'role', 'platform', 'tenant'
        )
        for device in devices:
            fraction, horizontal = read_partial_width(device)
            concept_device = ConceptDevice(
                concept=concept,
                name=(device.name or '') if include_device_names else '',
                status=ConceptDeviceStatusChoices.STATUS_EXISTING,
                device_type=device.device_type,
                role=device.role,
                platform=device.platform,
                tenant=device.tenant,
                position=device.position + shift,
                face=device.face or DeviceFaceChoices.FACE_FRONT,
                width_fraction=fraction,
                horizontal_position=horizontal,
                serial=device.serial if include_device_names else '',
                source_device=device,
            )
            try:
                concept_device.full_clean()
            except ValidationError:
                warnings.append(_(
                    '%(device)s from %(rack)s does not fit at its shifted position and was left out.'
                ) % {'device': device, 'rack': rack})
                continue
            concept_device.save()
            new_devices.append(concept_device)

    _copy_from_rack(rack_bottom, 0)
    _copy_from_rack(rack_top, bottom_height)

    for concept_device in new_devices:
        components.sync_components(concept_device)
    cable_summary = {'copied': 0, 'skipped': 0}
    cable_summary['copied'], cable_summary['skipped'] = components.copy_cables(new_devices)

    return concept, warnings, cable_summary


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
                face=device.face or DeviceFaceChoices.FACE_FRONT,
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
