import django_filters
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dcim.choices import CableTypeChoices, LinkStatusChoices
from dcim.models import DeviceRole, DeviceType, Rack, RackType, Site
from netbox.filtersets import NetBoxModelFilterSet
from tenancy.models import Tenant, TenantGroup

from .choices import ConceptComponentTypeChoices, ConceptDeviceStatusChoices, ConceptStatusChoices
from .models import ConceptCable, ConceptComponent, ConceptDevice, RackConcept

__all__ = (
    'ConceptCableFilterSet',
    'ConceptComponentFilterSet',
    'ConceptDeviceFilterSet',
    'RackConceptFilterSet',
)


class RackConceptFilterSet(NetBoxModelFilterSet):
    status = django_filters.MultipleChoiceFilter(
        choices=ConceptStatusChoices
    )
    tenant_group_id = django_filters.ModelMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        label=_('Tenant group (ID)')
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label=_('Tenant (ID)')
    )
    tenant = django_filters.ModelMultipleChoiceFilter(
        field_name='tenant__slug',
        queryset=Tenant.objects.all(),
        to_field_name='slug',
        label=_('Tenant (slug)')
    )
    rack_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RackType.objects.all(),
        label=_('Rack type (ID)')
    )
    source_rack_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Rack.objects.all(),
        label=_('Source rack (ID)')
    )
    default_site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label=_('Default site (ID)')
    )

    class Meta:
        model = RackConcept
        fields = (
            'id', 'name', 'status', 'form_factor', 'width', 'u_height', 'starting_unit', 'desc_units',
            'outer_width', 'outer_height', 'outer_depth', 'outer_unit', 'mounting_depth', 'airflow',
            'max_weight', 'description',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(comments__icontains=value)
        )


class ConceptDeviceFilterSet(NetBoxModelFilterSet):
    concept_id = django_filters.ModelMultipleChoiceFilter(
        queryset=RackConcept.objects.all(),
        label=_('Rack concept (ID)')
    )
    concept = django_filters.ModelMultipleChoiceFilter(
        field_name='concept__name',
        queryset=RackConcept.objects.all(),
        to_field_name='name',
        label=_('Rack concept (name)')
    )
    status = django_filters.MultipleChoiceFilter(
        choices=ConceptDeviceStatusChoices
    )
    device_type_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        label=_('Device type (ID)')
    )
    role_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceRole.objects.all(),
        label=_('Role (ID)')
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label=_('Tenant (ID)')
    )
    racked = django_filters.BooleanFilter(
        method='filter_racked',
        label=_('Has a position assigned')
    )

    class Meta:
        model = ConceptDevice
        fields = (
            'id', 'name', 'label', 'status', 'position', 'face', 'width_fraction', 'horizontal_position',
            'u_height', 'is_full_depth', 'serial', 'description',
        )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(label__icontains=value) |
            Q(serial__icontains=value) |
            Q(description__icontains=value) |
            Q(device_type__model__icontains=value)
        )

    def filter_racked(self, queryset, name, value):
        return queryset.filter(position__isnull=not value)


class ConceptComponentFilterSet(NetBoxModelFilterSet):
    device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=ConceptDevice.objects.all(),
        label=_('Concept device (ID)')
    )
    concept_id = django_filters.ModelMultipleChoiceFilter(
        field_name='device__concept',
        queryset=RackConcept.objects.all(),
        label=_('Rack concept (ID)')
    )
    component_type = django_filters.MultipleChoiceFilter(
        choices=ConceptComponentTypeChoices
    )
    connected = django_filters.BooleanFilter(
        method='filter_connected',
        label=_('Has a cable attached')
    )

    class Meta:
        model = ConceptComponent
        fields = ('id', 'name', 'label', 'component_type', 'port_type', 'positions', 'description')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) |
            Q(label__icontains=value) |
            Q(description__icontains=value)
        )

    def filter_connected(self, queryset, name, value):
        # A component is connected once it's referenced by a cable as either end.
        connected = (
            Q(pk__in=ConceptCable.objects.values_list('termination_a_id', flat=True)) |
            Q(pk__in=ConceptCable.objects.values_list('termination_b_id', flat=True))
        )
        return queryset.filter(connected) if value else queryset.exclude(connected)


class ConceptCableFilterSet(NetBoxModelFilterSet):
    concept_id = django_filters.ModelMultipleChoiceFilter(
        field_name='termination_a__device__concept',
        queryset=RackConcept.objects.all(),
        label=_('Rack concept (ID)')
    )
    status = django_filters.MultipleChoiceFilter(
        choices=LinkStatusChoices
    )
    type = django_filters.MultipleChoiceFilter(
        choices=CableTypeChoices
    )

    class Meta:
        model = ConceptCable
        fields = ('id', 'status', 'type', 'color', 'label', 'description')

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(label__icontains=value) |
            Q(description__icontains=value) |
            Q(termination_a__name__icontains=value) |
            Q(termination_b__name__icontains=value)
        )
