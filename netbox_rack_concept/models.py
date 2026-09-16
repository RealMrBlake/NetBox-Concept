from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from dcim.choices import (
    CableTypeChoices, DeviceFaceChoices, LinkStatusChoices, RackAirflowChoices, RackDimensionUnitChoices,
    RackFormFactorChoices, RackWidthChoices,
)
from netbox.models import NetBoxModel
from utilities.fields import ColorField

from .choices import (
    LANE_COUNT, ConceptComponentTypeChoices, ConceptDeviceStatusChoices, ConceptStatusChoices, WidthFractionChoices,
)

__all__ = (
    'ConceptCable',
    'ConceptComponent',
    'ConceptDevice',
    'ConceptDeployment',
    'ConceptPortMapping',
    'RackConcept',
)


class RackConcept(NetBoxModel):
    """
    A rack blueprint. It mirrors the geometry of dcim.Rack but is a separate model on
    purpose: a concept must never show up in the rack list, in rack elevations or in
    utilisation reports. It becomes a real rack only when it is deployed.
    """
    name = models.CharField(
        verbose_name=_('name'),
        max_length=100,
        unique=True
    )
    status = models.CharField(
        verbose_name=_('status'),
        max_length=50,
        choices=ConceptStatusChoices,
        default=ConceptStatusChoices.STATUS_DRAFT
    )
    tenant_group = models.ForeignKey(
        to='tenancy.TenantGroup',
        on_delete=models.PROTECT,
        related_name='rack_concepts',
        blank=True,
        null=True
    )
    tenant = models.ForeignKey(
        to='tenancy.Tenant',
        on_delete=models.PROTECT,
        related_name='rack_concepts',
        blank=True,
        null=True
    )

    # Rack geometry, mirroring dcim.RackBase
    form_factor = models.CharField(
        verbose_name=_('form factor'),
        choices=RackFormFactorChoices,
        max_length=50,
        blank=True
    )
    rack_type = models.ForeignKey(
        to='dcim.RackType',
        on_delete=models.PROTECT,
        related_name='rack_concepts',
        blank=True,
        null=True,
        help_text=_('Copy the geometry from a rack type instead of defining it here')
    )
    width = models.PositiveSmallIntegerField(
        verbose_name=_('width'),
        choices=RackWidthChoices,
        default=RackWidthChoices.WIDTH_19IN
    )
    u_height = models.PositiveSmallIntegerField(
        verbose_name=_('height (U)'),
        default=42,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    starting_unit = models.PositiveSmallIntegerField(
        verbose_name=_('starting unit'),
        default=1,
        validators=[MinValueValidator(1)]
    )
    desc_units = models.BooleanField(
        verbose_name=_('descending units'),
        default=False
    )
    outer_width = models.PositiveSmallIntegerField(blank=True, null=True)
    outer_height = models.PositiveSmallIntegerField(blank=True, null=True)
    outer_depth = models.PositiveSmallIntegerField(blank=True, null=True)
    outer_unit = models.CharField(
        max_length=50,
        choices=RackDimensionUnitChoices,
        blank=True
    )
    mounting_depth = models.PositiveSmallIntegerField(blank=True, null=True)
    airflow = models.CharField(
        max_length=50,
        choices=RackAirflowChoices,
        blank=True
    )
    max_weight = models.PositiveIntegerField(blank=True, null=True)

    # Defaults applied when the concept is deployed
    default_site = models.ForeignKey(
        to='dcim.Site',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
        help_text=_('Pre-selected when deploying this concept')
    )
    default_location = models.ForeignKey(
        to='dcim.Location',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )
    rack_role = models.ForeignKey(
        to='dcim.RackRole',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    # Provenance
    source_rack = models.ForeignKey(
        to='dcim.Rack',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
        help_text=_('The rack this concept was copied from')
    )

    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    clone_fields = (
        'status', 'tenant_group', 'tenant', 'form_factor', 'rack_type', 'width', 'u_height', 'starting_unit',
        'desc_units', 'outer_width', 'outer_height', 'outer_depth', 'outer_unit', 'mounting_depth', 'airflow',
        'max_weight', 'default_site', 'default_location', 'rack_role', 'description',
    )

    class Meta:
        ordering = ('name',)
        verbose_name = _('rack concept')
        verbose_name_plural = _('rack concepts')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_rack_concept:rackconcept', args=[self.pk])

    def get_status_color(self):
        return ConceptStatusChoices.colors.get(self.status)

    def clean(self):
        super().clean()
        if self.tenant and self.tenant_group and self.tenant.group_id != self.tenant_group_id:
            raise ValidationError({
                'tenant': _('Tenant {tenant} does not belong to group {group}.').format(
                    tenant=self.tenant, group=self.tenant_group
                )
            })

    def save(self, *args, **kwargs):
        # Keep the group in sync so tenant-group filtering works without a join.
        if self.tenant and not self.tenant_group:
            self.tenant_group = self.tenant.group
        super().save(*args, **kwargs)

    @property
    def units(self):
        """Unit numbers ordered as they are displayed, top first."""
        units = range(self.starting_unit, self.starting_unit + self.u_height)
        return list(units) if self.desc_units else list(reversed(units))

    @property
    def unit_range(self):
        """(lowest, highest_exclusive) unit numbers as Decimals."""
        return Decimal(self.starting_unit), Decimal(self.starting_unit + self.u_height)

    @property
    def total_u_used(self):
        return sum(d.effective_u_height for d in self.devices.all())

    @property
    def utilization(self):
        if not self.u_height:
            return 0
        return min(int(self.total_u_used / Decimal(self.u_height) * 100), 100)


class ConceptDevice(NetBoxModel):
    """
    A planned device inside a blueprint. It references a real dcim.DeviceType so that
    height, depth and manufacturer stay accurate, but it is never a dcim.Device and so
    never appears in the device list, in interface counts or in IPAM.
    """
    concept = models.ForeignKey(
        to=RackConcept,
        on_delete=models.CASCADE,
        related_name='devices'
    )
    name = models.CharField(
        verbose_name=_('name'),
        max_length=64,
        blank=True,
        help_text=_('Optional. Supports the placeholder {n} when deploying multiple racks.')
    )
    status = models.CharField(
        max_length=50,
        choices=ConceptDeviceStatusChoices,
        default=ConceptDeviceStatusChoices.STATUS_PLANNED
    )
    device_type = models.ForeignKey(
        to='dcim.DeviceType',
        on_delete=models.PROTECT,
        related_name='concept_devices',
        blank=True,
        null=True,
        help_text=_('Leave empty to reserve space without committing to a model')
    )
    role = models.ForeignKey(
        to='dcim.DeviceRole',
        on_delete=models.PROTECT,
        related_name='concept_devices',
        blank=True,
        null=True
    )
    platform = models.ForeignKey(
        to='dcim.Platform',
        on_delete=models.PROTECT,
        related_name='concept_devices',
        blank=True,
        null=True
    )
    tenant = models.ForeignKey(
        to='tenancy.Tenant',
        on_delete=models.PROTECT,
        related_name='concept_devices',
        blank=True,
        null=True,
        help_text=_('Overrides the tenant of the concept')
    )

    # Placement
    position = models.DecimalField(
        verbose_name=_('position (U)'),
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.5'))],
        help_text=_('Lowest unit occupied by the device. Empty means unracked.')
    )
    face = models.CharField(
        verbose_name=_('rack face'),
        max_length=50,
        choices=DeviceFaceChoices,
        default=DeviceFaceChoices.FACE_FRONT
    )
    width_fraction = models.PositiveSmallIntegerField(
        verbose_name=_('width'),
        choices=WidthFractionChoices,
        default=WidthFractionChoices.FRACTION_FULL,
        help_text=_('Horizontal share of the rack unit, as used by netbox_utilities')
    )
    horizontal_position = models.PositiveSmallIntegerField(
        verbose_name=_('horizontal position'),
        default=0,
        help_text=_('Slot index from the left, starting at 0')
    )

    # Overrides for placeholders without a device type
    u_height = models.DecimalField(
        verbose_name=_('height (U)'),
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text=_('Overrides the height of the device type')
    )
    is_full_depth = models.BooleanField(
        blank=True,
        null=True,
        help_text=_('Overrides the depth of the device type')
    )

    serial = models.CharField(max_length=50, blank=True)
    label = models.CharField(
        max_length=64,
        blank=True,
        help_text=_('Free text shown in the elevation instead of the name')
    )

    # Provenance
    source_device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    clone_fields = (
        'concept', 'status', 'device_type', 'role', 'platform', 'tenant', 'face', 'width_fraction',
    )

    class Meta:
        ordering = ('concept', '-position', 'horizontal_position', 'pk')
        indexes = (
            models.Index(fields=('concept', 'position'), name='nbrc_device_concept_pos_idx'),
        )
        verbose_name = _('concept device')
        verbose_name_plural = _('concept devices')

    def __str__(self):
        if self.name:
            return self.name
        if self.device_type:
            return f'{self.device_type} ({self.pk})'
        return f'Reserved space ({self.pk})'

    def get_absolute_url(self):
        return reverse('plugins:netbox_rack_concept:conceptdevice', args=[self.pk])

    def get_status_color(self):
        return ConceptDeviceStatusChoices.colors.get(self.status)

    @property
    def display_label(self):
        return self.label or self.name or (str(self.device_type) if self.device_type else _('Reserved'))

    @property
    def effective_u_height(self):
        if self.u_height is not None:
            return self.u_height
        if self.device_type:
            return Decimal(self.device_type.u_height)
        return Decimal('1')

    @property
    def effective_full_depth(self):
        if self.is_full_depth is not None:
            return self.is_full_depth
        if self.device_type:
            return self.device_type.is_full_depth
        return True

    @property
    def lane_span(self):
        """(start, end) lane indices on the LANE_COUNT grid."""
        lanes_per_slot = LANE_COUNT // self.width_fraction
        start = self.horizontal_position * lanes_per_slot
        return start, start + lanes_per_slot

    @property
    def unit_span(self):
        """(lowest, highest_exclusive) unit numbers, or None when unracked."""
        if self.position is None:
            return None
        return self.position, self.position + self.effective_u_height

    def occupies_face(self, face):
        return self.effective_full_depth or self.face == face

    def conflicts_with(self, other):
        """True when both devices claim the same physical space."""
        mine, theirs = self.unit_span, other.unit_span
        if mine is None or theirs is None:
            return False
        if mine[0] >= theirs[1] or theirs[0] >= mine[1]:
            return False
        # A full-depth device blocks both faces.
        if not (self.effective_full_depth or other.effective_full_depth) and self.face != other.face:
            return False
        my_lanes, their_lanes = self.lane_span, other.lane_span
        return my_lanes[0] < their_lanes[1] and their_lanes[0] < my_lanes[1]

    def clean(self):
        super().clean()

        if self.device_type is None and self.u_height is None:
            raise ValidationError({
                'u_height': _('Specify a device type or an explicit height.')
            })

        if self.horizontal_position >= self.width_fraction:
            raise ValidationError({
                'horizontal_position': _('With a width of 1/{fraction} the position must be between 0 and {max}.').format(
                    fraction=self.width_fraction, max=self.width_fraction - 1
                )
            })

        if self.position is None:
            return

        if self.position % Decimal('0.5') != 0:
            raise ValidationError({'position': _('Position must be a multiple of 0.5U.')})

        low, high = self.concept.unit_range
        span = self.unit_span
        if span[0] < low or span[1] > high:
            raise ValidationError({
                'position': _('A {height}U device at U{position} does not fit in a rack spanning U{low}-U{high}.').format(
                    height=self.effective_u_height, position=self.position, low=low, high=high - 1
                )
            })

        siblings = self.concept.devices.exclude(pk=self.pk).filter(position__isnull=False)
        for other in siblings.select_related('device_type'):
            if self.conflicts_with(other):
                raise ValidationError({
                    'position': _('Overlaps with {device} at U{position}.').format(
                        device=other, position=other.position
                    )
                })


class ConceptDeployment(models.Model):
    """Audit trail linking a blueprint to the real racks it produced."""
    concept = models.ForeignKey(
        to=RackConcept,
        on_delete=models.CASCADE,
        related_name='deployments'
    )
    rack = models.ForeignKey(
        to='dcim.Rack',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )
    rack_name = models.CharField(max_length=100)
    device_count = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        to='users.User',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True
    )

    class Meta:
        ordering = ('-created',)
        verbose_name = _('concept deployment')
        verbose_name_plural = _('concept deployments')

    def __str__(self):
        return f'{self.concept} → {self.rack_name}'


class ConceptComponent(NetBoxModel):
    """
    A pluggable point on a planned device - an interface, a front/rear port, a power
    port/outlet, or a console port. One shared model covers every kind rather than
    mirroring dcim's seven separate component models, since a blueprint only needs
    enough detail to say what a cable plugs into, not full per-type validation.

    Populated either by syncing a device's component templates (see components.py) or
    added by hand, which is the only option for placeholder devices without a device
    type.
    """
    device = models.ForeignKey(
        to=ConceptDevice,
        on_delete=models.CASCADE,
        related_name='components'
    )
    component_type = models.CharField(
        verbose_name=_('component type'),
        max_length=50,
        choices=ConceptComponentTypeChoices
    )
    name = models.CharField(
        verbose_name=_('name'),
        max_length=64
    )
    label = models.CharField(
        max_length=64,
        blank=True
    )
    port_type = models.CharField(
        verbose_name=_('type'),
        max_length=50,
        blank=True,
        help_text=_('Free text, e.g. "1000base-t" or "lc" - for reference only, not validated')
    )
    positions = models.PositiveSmallIntegerField(
        verbose_name=_('positions'),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(1024)],
        help_text=_('Front/rear ports only')
    )
    color = ColorField(blank=True)
    description = models.CharField(max_length=200, blank=True)

    clone_fields = ('device', 'component_type', 'port_type', 'positions')

    class Meta:
        ordering = ('device', 'component_type', 'name')
        constraints = (
            models.UniqueConstraint(fields=('device', 'name'), name='nbrc_component_unique_device_name'),
        )
        verbose_name = _('concept component')
        verbose_name_plural = _('concept components')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('plugins:netbox_rack_concept:conceptcomponent', args=[self.pk])

    @property
    def is_pass_through(self):
        return self.component_type in ConceptComponentTypeChoices.PATCH_TYPES

    @property
    def cable(self):
        return ConceptCable.objects.filter(
            models.Q(termination_a=self) | models.Q(termination_b=self)
        ).first()

    @property
    def is_connected(self):
        return self.cable is not None

    def get_paired_components(self):
        """
        For a front or rear port, the port(s) on the other side it passes through to -
        real patch panel behaviour: a signal entering a front port continues out
        whichever rear port (and position) it's mapped to, and vice versa.
        Returns a list of (component, own_position, other_position) tuples.
        """
        if self.component_type == ConceptComponentTypeChoices.TYPE_FRONT_PORT:
            return [
                (mapping.rear_component, mapping.front_position, mapping.rear_position)
                for mapping in self.front_mappings.select_related('rear_component')
            ]
        if self.component_type == ConceptComponentTypeChoices.TYPE_REAR_PORT:
            return [
                (mapping.front_component, mapping.rear_position, mapping.front_position)
                for mapping in self.rear_mappings.select_related('front_component')
            ]
        return []

    def clean(self):
        super().clean()
        if self.positions > 1 and not self.is_pass_through:
            raise ValidationError({
                'positions': _('Only front and rear ports can have more than one position.')
            })


class ConceptPortMapping(models.Model):
    """
    Maps a front port position to a rear port position, mirroring dcim's PortMapping.
    Not a NetBoxModel: like its real-world counterpart, this is wiring metadata, not a
    user-facing object with its own detail page.
    """
    front_component = models.ForeignKey(
        to=ConceptComponent,
        on_delete=models.CASCADE,
        related_name='front_mappings',
        limit_choices_to={'component_type': ConceptComponentTypeChoices.TYPE_FRONT_PORT}
    )
    rear_component = models.ForeignKey(
        to=ConceptComponent,
        on_delete=models.CASCADE,
        related_name='rear_mappings',
        limit_choices_to={'component_type': ConceptComponentTypeChoices.TYPE_REAR_PORT}
    )
    front_position = models.PositiveSmallIntegerField(default=1)
    rear_position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('front_component', 'front_position'), name='nbrc_portmapping_unique_front'
            ),
            models.UniqueConstraint(
                fields=('rear_component', 'rear_position'), name='nbrc_portmapping_unique_rear'
            ),
        )

    def __str__(self):
        return f'{self.front_component}:{self.front_position} → {self.rear_component}:{self.rear_position}'

    def clean(self):
        super().clean()
        if self.front_component_id and self.rear_component_id:
            if self.front_component.device_id != self.rear_component.device_id:
                raise ValidationError({
                    'rear_component': _('Front and rear port must belong to the same device.')
                })


class ConceptCable(NetBoxModel):
    """A planned connection between two components, on planned devices only."""
    termination_a = models.ForeignKey(
        to=ConceptComponent,
        on_delete=models.CASCADE,
        related_name='+'
    )
    termination_b = models.ForeignKey(
        to=ConceptComponent,
        on_delete=models.CASCADE,
        related_name='+'
    )
    status = models.CharField(
        max_length=50,
        choices=LinkStatusChoices,
        default=LinkStatusChoices.STATUS_CONNECTED
    )
    type = models.CharField(
        verbose_name=_('type'),
        max_length=50,
        choices=CableTypeChoices,
        blank=True
    )
    color = ColorField(blank=True)
    label = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    clone_fields = ('status', 'type', 'color')

    class Meta:
        ordering = ('pk',)
        verbose_name = _('concept cable')
        verbose_name_plural = _('concept cables')

    def __str__(self):
        return self.label or f'#{self.pk}'

    def get_absolute_url(self):
        return reverse('plugins:netbox_rack_concept:conceptcable', args=[self.pk])

    def get_status_color(self):
        return LinkStatusChoices.colors.get(self.status)

    def clean(self):
        super().clean()
        if not (self.termination_a_id and self.termination_b_id):
            return

        if self.termination_a_id == self.termination_b_id:
            raise ValidationError(_('A cable cannot connect a component to itself.'))

        if self.termination_a.device.concept_id != self.termination_b.device.concept_id:
            raise ValidationError(
                _('Both ends of a cable must belong to devices in the same rack concept.')
            )

        for field_name, endpoint in (('termination_a', self.termination_a), ('termination_b', self.termination_b)):
            conflict = ConceptCable.objects.exclude(pk=self.pk).filter(
                models.Q(termination_a=endpoint) | models.Q(termination_b=endpoint)
            ).first()
            if conflict:
                raise ValidationError({
                    field_name: _('%(component)s is already connected (%(cable)s).') % {
                        'component': endpoint, 'cable': conflict
                    }
                })
