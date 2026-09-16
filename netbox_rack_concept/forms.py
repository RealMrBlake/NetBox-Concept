from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.choices import DeviceFaceChoices, RackAirflowChoices, RackFormFactorChoices, RackWidthChoices
from dcim.models import DeviceRole, DeviceType, Location, Platform, Rack, RackRole, RackType, Site
from netbox.forms import NetBoxModelBulkEditForm, NetBoxModelFilterSetForm, NetBoxModelForm, NetBoxModelImportForm
from tenancy.models import Tenant, TenantGroup
from utilities.forms.fields import (
    CommentField, CSVChoiceField, CSVModelChoiceField, DynamicModelChoiceField, DynamicModelMultipleChoiceField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet
from utilities.forms.widgets import BulkEditNullBooleanSelect

from .choices import ConceptDeviceStatusChoices, ConceptStatusChoices, WidthFractionChoices
from .models import ConceptDevice, RackConcept

__all__ = (
    'ConceptDeployForm',
    'ConceptDeviceBulkEditForm',
    'ConceptDeviceFilterForm',
    'ConceptDeviceForm',
    'ConceptDeviceImportForm',
    'MergeConceptsForm',
    'MergeRacksForm',
    'RackConceptBulkEditForm',
    'RackConceptCloneForm',
    'RackConceptFilterForm',
    'RackConceptForm',
    'RackConceptImportForm',
    'RackCopyForm',
)


class RackConceptForm(NetBoxModelForm):
    tenant_group = DynamicModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        initial_params={'tenants': '$tenant'},
        label=_('Tenant group')
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        query_params={'group_id': '$tenant_group'},
        label=_('Tenant')
    )
    rack_type = DynamicModelChoiceField(
        queryset=RackType.objects.all(),
        required=False,
        label=_('Rack type')
    )
    rack_role = DynamicModelChoiceField(
        queryset=RackRole.objects.all(),
        required=False,
        label=_('Rack role')
    )
    default_site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        required=False,
        label=_('Default site')
    )
    default_location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={'site_id': '$default_site'},
        label=_('Default location')
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('name', 'status', 'description', 'tags', name=_('Concept')),
        FieldSet('tenant_group', 'tenant', name=_('Tenancy')),
        FieldSet(
            'rack_type', 'form_factor', 'width', 'u_height', 'starting_unit', 'desc_units', 'airflow',
            name=_('Geometry')
        ),
        FieldSet(
            'outer_width', 'outer_height', 'outer_depth', 'outer_unit', 'mounting_depth', 'max_weight',
            name=_('Dimensions')
        ),
        FieldSet('default_site', 'default_location', 'rack_role', name=_('Deployment defaults')),
    )

    class Meta:
        model = RackConcept
        fields = (
            'name', 'status', 'description', 'tenant_group', 'tenant', 'rack_type', 'form_factor', 'width',
            'u_height', 'starting_unit', 'desc_units', 'airflow', 'outer_width', 'outer_height', 'outer_depth',
            'outer_unit', 'mounting_depth', 'max_weight', 'default_site', 'default_location', 'rack_role',
            'comments', 'tags',
        )


class RackConceptFilterForm(NetBoxModelFilterSetForm):
    model = RackConcept

    status = forms.MultipleChoiceField(
        choices=ConceptStatusChoices,
        required=False
    )
    tenant_group_id = DynamicModelMultipleChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        label=_('Tenant group')
    )
    tenant_id = DynamicModelMultipleChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        label=_('Tenant')
    )
    width = forms.MultipleChoiceField(
        choices=RackWidthChoices,
        required=False
    )
    form_factor = forms.MultipleChoiceField(
        choices=RackFormFactorChoices,
        required=False
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('status', 'width', 'form_factor', name=_('Attributes')),
        FieldSet('tenant_group_id', 'tenant_id', name=_('Tenancy')),
    )


class RackConceptBulkEditForm(NetBoxModelBulkEditForm):
    model = RackConcept

    status = forms.ChoiceField(choices=ConceptStatusChoices, required=False)
    tenant_group = DynamicModelChoiceField(queryset=TenantGroup.objects.all(), required=False)
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        query_params={'group_id': '$tenant_group'}
    )
    description = forms.CharField(max_length=200, required=False)
    comments = CommentField()

    nullable_fields = ('tenant_group', 'tenant', 'description', 'comments')

    fieldsets = (
        FieldSet('status', 'description', name=_('Concept')),
        FieldSet('tenant_group', 'tenant', name=_('Tenancy')),
    )


class RackConceptImportForm(NetBoxModelImportForm):
    status = CSVChoiceField(choices=ConceptStatusChoices, required=False)
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        to_field_name='name',
        required=False
    )

    class Meta:
        model = RackConcept
        fields = (
            'name', 'status', 'description', 'tenant', 'form_factor', 'width', 'u_height', 'starting_unit',
            'desc_units', 'comments', 'tags',
        )


class ConceptDeviceForm(NetBoxModelForm):
    concept = DynamicModelChoiceField(
        queryset=RackConcept.objects.all(),
        label=_('Rack concept')
    )
    device_type = DynamicModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label=_('Device type')
    )
    role = DynamicModelChoiceField(
        queryset=DeviceRole.objects.all(),
        required=False,
        label=_('Role')
    )
    platform = DynamicModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        label=_('Platform')
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        label=_('Tenant')
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('concept', 'name', 'label', 'status', 'description', 'tags', name=_('Planned device')),
        FieldSet('device_type', 'role', 'platform', 'serial', name=_('Hardware')),
        FieldSet('position', 'face', 'width_fraction', 'horizontal_position', name=_('Placement')),
        FieldSet('u_height', 'is_full_depth', name=_('Overrides')),
        FieldSet('tenant', name=_('Tenancy')),
    )

    class Meta:
        model = ConceptDevice
        fields = (
            'concept', 'name', 'label', 'status', 'description', 'device_type', 'role', 'platform', 'serial',
            'position', 'face', 'width_fraction', 'horizontal_position', 'u_height', 'is_full_depth', 'tenant',
            'comments', 'tags',
        )


class ConceptDeviceFilterForm(NetBoxModelFilterSetForm):
    model = ConceptDevice

    concept_id = DynamicModelMultipleChoiceField(
        queryset=RackConcept.objects.all(),
        required=False,
        label=_('Rack concept')
    )
    status = forms.MultipleChoiceField(choices=ConceptDeviceStatusChoices, required=False)
    device_type_id = DynamicModelMultipleChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        label=_('Device type')
    )
    role_id = DynamicModelMultipleChoiceField(
        queryset=DeviceRole.objects.all(),
        required=False,
        label=_('Role')
    )
    face = forms.MultipleChoiceField(choices=DeviceFaceChoices, required=False)
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('concept_id', 'status', 'face', name=_('Placement')),
        FieldSet('device_type_id', 'role_id', name=_('Hardware')),
    )


class ConceptDeviceBulkEditForm(NetBoxModelBulkEditForm):
    model = ConceptDevice

    status = forms.ChoiceField(choices=ConceptDeviceStatusChoices, required=False)
    role = DynamicModelChoiceField(queryset=DeviceRole.objects.all(), required=False)
    platform = DynamicModelChoiceField(queryset=Platform.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    face = forms.ChoiceField(choices=DeviceFaceChoices, required=False)
    width_fraction = forms.ChoiceField(choices=WidthFractionChoices, required=False)
    is_full_depth = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect())
    description = forms.CharField(max_length=200, required=False)

    nullable_fields = ('role', 'platform', 'tenant', 'description', 'is_full_depth')

    fieldsets = (
        FieldSet('status', 'role', 'platform', 'description', name=_('Planned device')),
        FieldSet('face', 'width_fraction', 'is_full_depth', name=_('Placement')),
        FieldSet('tenant', name=_('Tenancy')),
    )


class ConceptDeviceImportForm(NetBoxModelImportForm):
    concept = CSVModelChoiceField(
        queryset=RackConcept.objects.all(),
        to_field_name='name'
    )
    device_type = CSVModelChoiceField(
        queryset=DeviceType.objects.all(),
        to_field_name='model',
        required=False
    )
    role = CSVModelChoiceField(
        queryset=DeviceRole.objects.all(),
        to_field_name='name',
        required=False
    )
    status = CSVChoiceField(choices=ConceptDeviceStatusChoices, required=False)
    face = CSVChoiceField(choices=DeviceFaceChoices, required=False)

    class Meta:
        model = ConceptDevice
        fields = (
            'concept', 'name', 'label', 'status', 'device_type', 'role', 'position', 'face', 'width_fraction',
            'horizontal_position', 'u_height', 'is_full_depth', 'description', 'tags',
        )


#
# Action forms
#

class RackCopyForm(forms.Form):
    """Copy an existing dcim.Rack into a new blueprint."""
    name = forms.CharField(
        label=_('Concept name'),
        max_length=100
    )
    status = forms.ChoiceField(
        choices=ConceptStatusChoices,
        initial=ConceptStatusChoices.STATUS_DRAFT
    )
    tenant_group = DynamicModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        label=_('Tenant group')
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        query_params={'group_id': '$tenant_group'},
        label=_('Tenant')
    )
    include_devices = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Copy installed devices'),
        help_text=_('Snapshot every device currently mounted in the rack')
    )
    include_device_names = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Keep device names'),
        help_text=_('Unchecked, only the device type and position are copied')
    )
    override_width = forms.ChoiceField(
        choices=(('', _('Same as rack')),) + tuple(RackWidthChoices),
        required=False,
        label=_('Width')
    )
    override_u_height = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        label=_('Height (U)'),
        help_text=_('Leave empty to keep the rack\'s own height. Devices that no longer fit are left out.')
    )
    override_starting_unit = forms.IntegerField(
        required=False,
        min_value=1,
        label=_('Starting unit'),
        help_text=_('Leave empty to keep the rack\'s own starting unit')
    )
    description = forms.CharField(max_length=200, required=False)

    fieldsets = (
        FieldSet('name', 'status', 'description', name=_('Concept')),
        FieldSet('tenant_group', 'tenant', name=_('Tenancy')),
        FieldSet('include_devices', 'include_device_names', name=_('Content')),
        FieldSet(
            'override_width', 'override_u_height', 'override_starting_unit',
            name=_('Concept size (optional)')
        ),
    )

    def clean_override_width(self):
        value = self.cleaned_data['override_width']
        return int(value) if value else None


class MergeConceptsForm(forms.Form):
    """Stack two blueprints (e.g. two half-height racks) into one taller concept."""
    name = forms.CharField(
        label=_('New concept name'),
        max_length=100
    )
    status = forms.ChoiceField(
        choices=ConceptStatusChoices,
        initial=ConceptStatusChoices.STATUS_DRAFT
    )
    tenant_group = DynamicModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        label=_('Tenant group')
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        query_params={'group_id': '$tenant_group'},
        label=_('Tenant')
    )
    concept_bottom = DynamicModelChoiceField(
        queryset=RackConcept.objects.all(),
        label=_('Bottom concept'),
        help_text=_('Keeps its planned positions unchanged')
    )
    concept_top = DynamicModelChoiceField(
        queryset=RackConcept.objects.all(),
        label=_('Top concept'),
        help_text=_("Its devices are shifted up by the bottom concept's height")
    )
    width = forms.ChoiceField(
        choices=RackWidthChoices,
        initial=RackWidthChoices.WIDTH_19IN,
        label=_('Width of the combined rack')
    )
    u_height = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        label=_('Height (U)'),
        help_text=_('Leave empty to use the sum of both heights')
    )
    starting_unit = forms.IntegerField(
        initial=1,
        min_value=1,
        label=_('Starting unit')
    )
    description = forms.CharField(max_length=200, required=False)

    fieldsets = (
        FieldSet('name', 'status', 'description', name=_('Concept')),
        FieldSet('tenant_group', 'tenant', name=_('Tenancy')),
        FieldSet('concept_bottom', 'concept_top', name=_('Sources')),
        FieldSet('width', 'u_height', 'starting_unit', name=_('Combined size')),
    )

    def clean_width(self):
        return int(self.cleaned_data['width'])

    def clean(self):
        cleaned = super().clean()
        bottom, top = cleaned.get('concept_bottom'), cleaned.get('concept_top')
        if bottom and top and bottom.pk == top.pk:
            raise forms.ValidationError(_('Choose two different concepts to merge.'))
        return cleaned


class MergeRacksForm(forms.Form):
    """Combine two existing racks directly into one new, stacked blueprint."""
    name = forms.CharField(
        label=_('Concept name'),
        max_length=100
    )
    status = forms.ChoiceField(
        choices=ConceptStatusChoices,
        initial=ConceptStatusChoices.STATUS_DRAFT
    )
    tenant_group = DynamicModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        label=_('Tenant group')
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        query_params={'group_id': '$tenant_group'},
        label=_('Tenant')
    )
    rack_bottom = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        label=_('Bottom rack'),
        help_text=_('Keeps its planned positions unchanged')
    )
    rack_top = DynamicModelChoiceField(
        queryset=Rack.objects.all(),
        label=_('Top rack'),
        help_text=_("Its devices are shifted up by the bottom rack's height")
    )
    include_devices = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Copy installed devices')
    )
    include_device_names = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Keep device names')
    )
    width = forms.ChoiceField(
        choices=RackWidthChoices,
        initial=RackWidthChoices.WIDTH_19IN,
        label=_('Width of the combined rack')
    )
    u_height = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        label=_('Height (U)'),
        help_text=_('Leave empty to use the sum of both heights')
    )
    starting_unit = forms.IntegerField(
        initial=1,
        min_value=1,
        label=_('Starting unit')
    )
    description = forms.CharField(max_length=200, required=False)

    fieldsets = (
        FieldSet('name', 'status', 'description', name=_('Concept')),
        FieldSet('tenant_group', 'tenant', name=_('Tenancy')),
        FieldSet('rack_bottom', 'rack_top', name=_('Sources')),
        FieldSet('include_devices', 'include_device_names', name=_('Content')),
        FieldSet('width', 'u_height', 'starting_unit', name=_('Combined size')),
    )

    def clean_width(self):
        return int(self.cleaned_data['width'])

    def clean(self):
        cleaned = super().clean()
        bottom, top = cleaned.get('rack_bottom'), cleaned.get('rack_top')
        if bottom and top and bottom.pk == top.pk:
            raise forms.ValidationError(_('Choose two different racks to merge.'))
        return cleaned


class RackConceptCloneForm(forms.Form):
    """Duplicate a blueprint, for building variants."""
    name = forms.CharField(
        label=_('New concept name'),
        max_length=100
    )
    status = forms.ChoiceField(
        choices=ConceptStatusChoices,
        initial=ConceptStatusChoices.STATUS_DRAFT
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        label=_('Tenant')
    )
    include_devices = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Copy planned devices')
    )

    fieldsets = (
        FieldSet('name', 'status', 'tenant', 'include_devices'),
    )


class ConceptDeployForm(forms.Form):
    """Materialise a blueprint as one or more real racks."""
    name_pattern = forms.CharField(
        label=_('Rack name'),
        max_length=100,
        help_text=_('Use {n} for the sequence number, e.g. "DC1-R{n}". Zero-pad with {n:02d}.')
    )
    count = forms.IntegerField(
        label=_('Number of racks'),
        min_value=1,
        max_value=100,
        initial=1
    )
    start_index = forms.IntegerField(
        label=_('First sequence number'),
        initial=1
    )
    site = DynamicModelChoiceField(
        queryset=Site.objects.all(),
        label=_('Site')
    )
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        query_params={'site_id': '$site'},
        label=_('Location')
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        label=_('Tenant')
    )
    create_devices = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Create devices'),
        help_text=_('Create a real device for every planned device that has a device type and a position')
    )
    device_name_pattern = forms.CharField(
        max_length=100,
        required=False,
        label=_('Device name'),
        help_text=_('Optional. {rack} and {name} are replaced, e.g. "{rack}-{name}". '
                    'Empty keeps the planned name.')
    )
    skip_unnamed_devices = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Skip devices without a name'),
        help_text=_('Unchecked, unnamed planned devices are created as unnamed devices')
    )

    fieldsets = (
        FieldSet('name_pattern', 'count', 'start_index', name=_('Racks')),
        FieldSet('site', 'location', 'tenant', name=_('Placement')),
        FieldSet('create_devices', 'device_name_pattern', 'skip_unnamed_devices', name=_('Devices')),
    )

    def __init__(self, *args, concept=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.concept = concept
        if concept and not self.is_bound:
            self.fields['name_pattern'].initial = concept.name
            if concept.default_site:
                self.fields['site'].initial = concept.default_site.pk
            if concept.default_location:
                self.fields['location'].initial = concept.default_location.pk
            if concept.tenant:
                self.fields['tenant'].initial = concept.tenant.pk

    def clean_name_pattern(self):
        pattern = self.cleaned_data['name_pattern']
        try:
            pattern.format(n=1)
        except (IndexError, KeyError, ValueError) as exc:
            raise forms.ValidationError(
                _('Invalid name pattern: {error}').format(error=exc)
            )
        return pattern

    def clean(self):
        cleaned = super().clean()
        pattern = cleaned.get('name_pattern')
        count = cleaned.get('count')
        start = cleaned.get('start_index')
        site = cleaned.get('site')
        if not (pattern and count and start is not None and site):
            return cleaned

        names = [pattern.format(n=i) for i in range(start, start + count)]
        if len(set(names)) != len(names):
            raise forms.ValidationError({
                'name_pattern': _('The pattern produces duplicate names. Include {n} when creating more than one rack.')
            })
        clashes = Rack.objects.filter(site=site, name__in=names).values_list('name', flat=True)
        if clashes:
            raise forms.ValidationError({
                'name_pattern': _('These racks already exist at {site}: {names}').format(
                    site=site, names=', '.join(sorted(clashes))
                )
            })
        cleaned['rack_names'] = names
        return cleaned
