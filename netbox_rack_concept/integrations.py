"""
Optional interoperability with the two plugins this one is meant to sit next to.

Neither is a hard dependency. Everything here degrades to a no-op when the other
plugin is absent, so the concept plugin works on a bare NetBox 4.6 install.

* netbox_utilities  -- partial-width rack devices (several devices per rack unit).
  The field names are read from PLUGINS_CONFIG so that a rename on their side is a
  configuration change here, not a code change.

* netbox-reorder-rack -- drag & drop ordering of *real* racks. Concepts get their
  own drag & drop elevation (see static/, templates/) because that plugin operates on
  dcim.Device querysets, which a concept deliberately has none of. Once a concept has
  been deployed the resulting rack is an ordinary rack and reorder-rack applies to it.
"""
import logging

from django.apps import apps
from django.conf import settings

logger = logging.getLogger('netbox.plugins.netbox_rack_concept')

__all__ = (
    'apply_partial_width',
    'get_partial_width_adapter',
    'read_partial_width',
    'stage_partial_width',
    'reorder_rack_installed',
)


def _config():
    return settings.PLUGINS_CONFIG.get('netbox_rack_concept', {})


def plugin_installed(name):
    return name in settings.PLUGINS


def reorder_rack_installed():
    return plugin_installed('netbox_reorder_rack')


class PartialWidthAdapter:
    """
    Wraps whichever shape netbox_utilities uses to store partial-width data:
    either extra fields on dcim.Device, or a side model with a FK to the device.
    """

    def __init__(self, model, device_field, fraction_field, position_field, position_base=0):
        self.model = model
        self.device_field = device_field
        self.fraction_field = fraction_field
        self.position_field = position_field
        self.position_base = position_base

    def write(self, device, fraction, position):
        position += self.position_base
        if self.model is None:
            # Fields live directly on the Device.
            setattr(device, self.fraction_field, fraction)
            setattr(device, self.position_field, position)
            device.save(update_fields=[self.fraction_field, self.position_field])
            return

        self.model.objects.update_or_create(
            **{self.device_field: device},
            defaults={
                self.fraction_field: fraction,
                self.position_field: position,
            }
        )

    def read(self, device):
        if self.model is None:
            return (
                getattr(device, self.fraction_field, None),
                getattr(device, self.position_field, None),
            )
        obj = self.model.objects.filter(**{self.device_field: device}).first()
        if obj is None:
            return None, None
        position = getattr(obj, self.position_field, None)
        if position is not None:
            position = max(int(position) - self.position_base, 0)
        return getattr(obj, self.fraction_field, None), position


_ADAPTER_CACHE = {}

# Defaults matching netbox_utilities.DeviceRackPlacement. Earlier versions of this plugin
# shipped a model name that never existed; configurations copied from that are migrated.
UTILITIES_PARTIAL_WIDTH = {
    'model': 'netbox_utilities.DeviceRackPlacement',
    'device_field': 'device',
    'fraction_field': 'width',
    'position_field': 'horizontal_position',
    'position_base': 1,
}
LEGACY_PARTIAL_WIDTH_MODEL = 'netbox_utilities.RackDevicePosition'


def get_partial_width_adapter():
    """Return a PartialWidthAdapter, or None when partial width is unavailable."""
    if 'adapter' in _ADAPTER_CACHE:
        return _ADAPTER_CACHE['adapter']

    adapter = None
    config = _config().get('partial_width') or {}
    if config.get('model') == LEGACY_PARTIAL_WIDTH_MODEL:
        config = {**config, **UTILITIES_PARTIAL_WIDTH}

    if config.get('enabled') and plugin_installed('netbox_utilities'):
        fraction_field = config.get('fraction_field', UTILITIES_PARTIAL_WIDTH['fraction_field'])
        position_field = config.get('position_field', UTILITIES_PARTIAL_WIDTH['position_field'])
        position_base = int(config.get('position_base', 0))
        model_path = config.get('model')
        model = None

        if model_path:
            try:
                model = apps.get_model(model_path)
            except (LookupError, ValueError):
                logger.warning(
                    'netbox_rack_concept: partial-width model %r not found; falling back to Device fields. '
                    'Adjust PLUGINS_CONFIG["netbox_rack_concept"]["partial_width"] to match netbox_utilities.',
                    model_path
                )

        if model is None:
            device_model = apps.get_model('dcim', 'Device')
            field_names = {f.name for f in device_model._meta.get_fields()}
            if fraction_field in field_names and position_field in field_names:
                adapter = PartialWidthAdapter(None, None, fraction_field, position_field)
            else:
                logger.warning(
                    'netbox_rack_concept: netbox_utilities is installed but its partial-width storage could not '
                    'be located. Partial-width values will not be written when deploying concepts.'
                )
        else:
            adapter = PartialWidthAdapter(
                model, config.get('device_field', 'device'), fraction_field, position_field, position_base
            )

    _ADAPTER_CACHE['adapter'] = adapter
    return adapter


def stage_partial_width(device, concept_device):
    """
    Announce the partial width of a not yet saved device to netbox_utilities, so that its
    collision check treats devices sharing a rack unit side by side instead of overlapping.
    """
    if concept_device.width_fraction == 1 or get_partial_width_adapter() is None:
        return False
    try:
        from netbox_utilities.rack_width import stage_width_position
    except ImportError:
        return False
    adapter = get_partial_width_adapter()
    stage_width_position(
        device, concept_device.width_fraction, concept_device.horizontal_position + adapter.position_base
    )
    return True


def apply_partial_width(device, concept_device):
    """
    Persist the partial-width placement of a concept device onto the real device that
    was created from it. Full-width devices need nothing written.
    """
    if concept_device.width_fraction == 1:
        return False
    adapter = get_partial_width_adapter()
    if adapter is None:
        return False
    try:
        adapter.write(device, concept_device.width_fraction, concept_device.horizontal_position)
        return True
    except Exception as exc:  # pragma: no cover - depends on the other plugin's schema
        logger.warning('netbox_rack_concept: could not write partial-width data for %s: %s', device, exc)
        return False


def read_partial_width(device):
    """Read partial-width placement off a real device when copying a rack into a concept."""
    adapter = get_partial_width_adapter()
    if adapter is None:
        return 1, 0
    try:
        fraction, position = adapter.read(device)
    except Exception as exc:  # pragma: no cover
        logger.warning('netbox_rack_concept: could not read partial-width data for %s: %s', device, exc)
        return 1, 0
    return int(fraction or 1), int(position or 0)
