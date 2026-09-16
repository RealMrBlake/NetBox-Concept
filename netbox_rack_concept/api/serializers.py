from rest_framework import serializers

from dcim.api.serializers import (
    DeviceRoleSerializer, DeviceTypeSerializer, LocationSerializer, PlatformSerializer, RackRoleSerializer,
    RackSerializer, RackTypeSerializer, SiteSerializer,
)
from netbox.api.serializers import NetBoxModelSerializer
from tenancy.api.serializers import TenantGroupSerializer, TenantSerializer

from ..choices import ConceptStatusChoices
from ..models import ConceptDeployment, ConceptDevice, RackConcept

__all__ = (
    'ConceptDeploySerializer',
    'ConceptDeploymentSerializer',
    'ConceptDeviceSerializer',
    'RackConceptCloneSerializer',
    'RackConceptSerializer',
    'RackCopySerializer',
)


class RackConceptSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_rack_concept-api:rackconcept-detail'
    )
    tenant = TenantSerializer(nested=True, required=False, allow_null=True)
    tenant_group = TenantGroupSerializer(nested=True, required=False, allow_null=True)
    rack_type = RackTypeSerializer(nested=True, required=False, allow_null=True)
    rack_role = RackRoleSerializer(nested=True, required=False, allow_null=True)
    default_site = SiteSerializer(nested=True, required=False, allow_null=True)
    default_location = LocationSerializer(nested=True, required=False, allow_null=True)
    source_rack = RackSerializer(nested=True, required=False, allow_null=True)
    device_count = serializers.IntegerField(read_only=True)
    utilization = serializers.IntegerField(read_only=True)

    class Meta:
        model = RackConcept
        fields = (
            'id', 'url', 'display_url', 'display', 'name', 'status', 'description', 'tenant_group', 'tenant',
            'rack_type', 'form_factor', 'width', 'u_height', 'starting_unit', 'desc_units', 'outer_width',
            'outer_height', 'outer_depth', 'outer_unit', 'mounting_depth', 'airflow', 'max_weight',
            'default_site', 'default_location', 'rack_role', 'source_rack', 'comments', 'tags',
            'custom_fields', 'created', 'last_updated', 'device_count', 'utilization',
        )
        brief_fields = ('id', 'url', 'display', 'name', 'status', 'u_height', 'description')


class ConceptDeviceSerializer(NetBoxModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name='plugins-api:netbox_rack_concept-api:conceptdevice-detail'
    )
    concept = RackConceptSerializer(nested=True)
    device_type = DeviceTypeSerializer(nested=True, required=False, allow_null=True)
    role = DeviceRoleSerializer(nested=True, required=False, allow_null=True)
    platform = PlatformSerializer(nested=True, required=False, allow_null=True)
    tenant = TenantSerializer(nested=True, required=False, allow_null=True)
    effective_u_height = serializers.DecimalField(
        max_digits=4, decimal_places=1, read_only=True
    )

    class Meta:
        model = ConceptDevice
        fields = (
            'id', 'url', 'display_url', 'display', 'concept', 'name', 'label', 'status', 'device_type', 'role',
            'platform', 'tenant', 'position', 'face', 'width_fraction', 'horizontal_position', 'u_height',
            'is_full_depth', 'effective_u_height', 'serial', 'source_device', 'description', 'comments', 'tags',
            'custom_fields', 'created', 'last_updated',
        )
        brief_fields = ('id', 'url', 'display', 'name', 'position', 'face', 'device_type')


class ConceptDeploymentSerializer(serializers.ModelSerializer):
    rack = RackSerializer(nested=True, read_only=True, allow_null=True)

    class Meta:
        model = ConceptDeployment
        fields = ('id', 'rack', 'rack_name', 'device_count', 'user', 'created')


#
# Action payloads
#

class RackCopySerializer(serializers.Serializer):
    """POST body for copying a real rack into a new concept."""
    rack = serializers.PrimaryKeyRelatedField(queryset=None)
    name = serializers.CharField(max_length=100)
    status = serializers.ChoiceField(choices=ConceptStatusChoices, default=ConceptStatusChoices.STATUS_DRAFT)
    tenant = serializers.PrimaryKeyRelatedField(queryset=None, required=False, allow_null=True)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    include_devices = serializers.BooleanField(default=True)
    include_device_names = serializers.BooleanField(default=True)

    def __init__(self, *args, **kwargs):
        from dcim.models import Rack
        from tenancy.models import Tenant
        super().__init__(*args, **kwargs)
        self.fields['rack'].queryset = Rack.objects.all()
        self.fields['tenant'].queryset = Tenant.objects.all()


class RackConceptCloneSerializer(serializers.Serializer):
    """POST body for duplicating a concept."""
    name = serializers.CharField(max_length=100)
    status = serializers.ChoiceField(choices=ConceptStatusChoices, default=ConceptStatusChoices.STATUS_DRAFT)
    tenant = serializers.PrimaryKeyRelatedField(queryset=None, required=False, allow_null=True)
    include_devices = serializers.BooleanField(default=True)

    def __init__(self, *args, **kwargs):
        from tenancy.models import Tenant
        super().__init__(*args, **kwargs)
        self.fields['tenant'].queryset = Tenant.objects.all()


class ConceptDeploySerializer(serializers.Serializer):
    """POST body for materialising a concept."""
    name_pattern = serializers.CharField(max_length=100)
    count = serializers.IntegerField(min_value=1, max_value=100, default=1)
    start_index = serializers.IntegerField(default=1)
    site = serializers.PrimaryKeyRelatedField(queryset=None)
    location = serializers.PrimaryKeyRelatedField(queryset=None, required=False, allow_null=True)
    tenant = serializers.PrimaryKeyRelatedField(queryset=None, required=False, allow_null=True)
    create_devices = serializers.BooleanField(default=True)
    device_name_pattern = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    skip_unnamed_devices = serializers.BooleanField(default=True)
    dry_run = serializers.BooleanField(
        default=False,
        help_text='Return the planned rack names and warnings without creating anything'
    )

    def __init__(self, *args, **kwargs):
        from dcim.models import Location, Site
        from tenancy.models import Tenant
        super().__init__(*args, **kwargs)
        self.fields['site'].queryset = Site.objects.all()
        self.fields['location'].queryset = Location.objects.all()
        self.fields['tenant'].queryset = Tenant.objects.all()

    def validate(self, attrs):
        from dcim.models import Rack
        try:
            names = [
                attrs['name_pattern'].format(n=i)
                for i in range(attrs['start_index'], attrs['start_index'] + attrs['count'])
            ]
        except (IndexError, KeyError, ValueError) as exc:
            raise serializers.ValidationError({'name_pattern': f'Invalid pattern: {exc}'})

        if len(set(names)) != len(names):
            raise serializers.ValidationError({
                'name_pattern': 'The pattern produces duplicate names. Include {n} when creating more than one rack.'
            })
        clashes = list(Rack.objects.filter(site=attrs['site'], name__in=names).values_list('name', flat=True))
        if clashes:
            raise serializers.ValidationError({
                'name_pattern': f'These racks already exist at the site: {", ".join(sorted(clashes))}'
            })

        attrs['rack_names'] = names
        return attrs
