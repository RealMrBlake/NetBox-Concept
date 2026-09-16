import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, columns

from .models import ConceptDeployment, ConceptDevice, RackConcept

__all__ = (
    'ConceptDeploymentTable',
    'ConceptDeviceElevationTable',
    'ConceptDeviceTable',
    'RackConceptTable',
)


class RackConceptTable(NetBoxTable):
    name = tables.Column(linkify=True)
    status = columns.ChoiceFieldColumn()
    tenant_group = tables.Column(linkify=True, verbose_name=_('Tenant group'))
    tenant = tables.Column(linkify=True)
    rack_type = tables.Column(linkify=True)
    device_count = columns.LinkedCountColumn(
        viewname='plugins:netbox_rack_concept:conceptdevice_list',
        url_params={'concept_id': 'pk'},
        verbose_name=_('Devices')
    )
    utilization = columns.UtilizationColumn(
        accessor='utilization',
        orderable=False,
        verbose_name=_('Utilization')
    )
    source_rack = tables.Column(linkify=True, verbose_name=_('Copied from'))
    comments = columns.MarkdownColumn()
    tags = columns.TagColumn(url_name='plugins:netbox_rack_concept:rackconcept_list')

    class Meta(NetBoxTable.Meta):
        model = RackConcept
        fields = (
            'pk', 'id', 'name', 'status', 'tenant_group', 'tenant', 'rack_type', 'form_factor', 'width',
            'u_height', 'starting_unit', 'desc_units', 'device_count', 'utilization', 'source_rack',
            'description', 'comments', 'tags', 'created', 'last_updated',
        )
        default_columns = (
            'name', 'status', 'tenant', 'u_height', 'width', 'device_count', 'utilization', 'description',
        )


class ConceptDeviceTable(NetBoxTable):
    name = tables.Column(linkify=True, empty_values=())
    concept = tables.Column(linkify=True, verbose_name=_('Concept'))
    status = columns.ChoiceFieldColumn()
    device_type = tables.Column(linkify=True, verbose_name=_('Type'))
    manufacturer = tables.Column(
        accessor='device_type__manufacturer',
        linkify=True,
        verbose_name=_('Manufacturer')
    )
    role = columns.ColoredLabelColumn()
    platform = tables.Column(linkify=True)
    tenant = tables.Column(linkify=True)
    position = tables.Column(verbose_name=_('Position (U)'))
    # A plain column, not ChoiceFieldColumn: WidthFractionChoices carries no colours.
    width_fraction = tables.Column(
        accessor='get_width_fraction_display',
        order_by='width_fraction',
        verbose_name=_('Width')
    )
    source_device = tables.Column(linkify=True, verbose_name=_('Copied from'))
    comments = columns.MarkdownColumn()
    tags = columns.TagColumn(url_name='plugins:netbox_rack_concept:conceptdevice_list')

    class Meta(NetBoxTable.Meta):
        model = ConceptDevice
        fields = (
            'pk', 'id', 'name', 'label', 'concept', 'status', 'device_type', 'manufacturer', 'role', 'platform',
            'tenant', 'position', 'face', 'width_fraction', 'horizontal_position', 'u_height', 'is_full_depth',
            'serial', 'source_device', 'description', 'comments', 'tags', 'created', 'last_updated',
        )
        default_columns = (
            'name', 'concept', 'status', 'device_type', 'role', 'position', 'face', 'width_fraction',
        )

    def render_name(self, record):
        return record.display_label


class ConceptDeviceElevationTable(ConceptDeviceTable):
    """Device list shown on the concept detail page, without the redundant concept column."""

    class Meta(ConceptDeviceTable.Meta):
        default_columns = (
            'name', 'status', 'device_type', 'role', 'position', 'face', 'width_fraction', 'horizontal_position',
        )


class ConceptDeploymentTable(tables.Table):
    rack_name = tables.Column(verbose_name=_('Rack'))
    rack = tables.Column(linkify=True, verbose_name=_('Link'))
    device_count = tables.Column(verbose_name=_('Devices'))
    user = tables.Column(verbose_name=_('Deployed by'))
    created = columns.DateTimeColumn(verbose_name=_('Deployed'))

    class Meta:
        model = ConceptDeployment
        fields = ('rack_name', 'rack', 'device_count', 'user', 'created')
        attrs = {'class': 'table table-hover object-list'}
        empty_text = _('This concept has not been deployed yet.')
