import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, columns

from .models import ConceptCable, ConceptComponent, ConceptDeployment, ConceptDevice, RackConcept

__all__ = (
    'ConceptCableTable',
    'ConceptComponentTable',
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


class ConceptComponentTable(NetBoxTable):
    name = tables.Column(linkify=True)
    device = tables.Column(linkify=True, verbose_name=_('Device'))
    concept = tables.Column(accessor='device__concept', linkify=True, verbose_name=_('Concept'))
    component_type = columns.ChoiceFieldColumn()
    color = columns.ColorColumn()
    connection = tables.Column(
        accessor='cable', linkify=True, orderable=False, verbose_name=_('Connection'), empty_values=()
    )
    connect = tables.TemplateColumn(
        template_code="""
            {% load i18n %}
            {% if not record.is_connected %}
              <a href="{% url 'plugins:netbox_rack_concept:conceptcable_add' %}?concept={{ record.device.concept_id }}&amp;termination_a_device={{ record.device_id }}&amp;termination_a={{ record.pk }}"
                 class="btn btn-sm btn-primary">{% trans "Connect" %}</a>
            {% endif %}
        """,
        verbose_name='',
        orderable=False
    )
    tags = columns.TagColumn(url_name='plugins:netbox_rack_concept:conceptcomponent_list')

    class Meta(NetBoxTable.Meta):
        model = ConceptComponent
        fields = (
            'pk', 'id', 'name', 'label', 'device', 'concept', 'component_type', 'port_type', 'positions', 'color',
            'connection', 'connect', 'description', 'tags', 'created', 'last_updated',
        )
        default_columns = ('name', 'device', 'component_type', 'port_type', 'connection', 'connect')

    def render_connection(self, value, record):
        return value if value else _('Not connected')


class ConceptCableTable(NetBoxTable):
    id = tables.Column(linkify=True, verbose_name=_('ID'))
    label = tables.Column(linkify=True)
    concept = tables.Column(accessor='termination_a__device__concept', linkify=True, verbose_name=_('Concept'))
    status = columns.ChoiceFieldColumn()
    type = columns.ChoiceFieldColumn()
    color = columns.ColorColumn()
    termination_a_device = tables.Column(
        accessor='termination_a__device', linkify=True, verbose_name=_('Device A')
    )
    termination_a = tables.Column(linkify=True, verbose_name=_('Component A'))
    termination_b_device = tables.Column(
        accessor='termination_b__device', linkify=True, verbose_name=_('Device B')
    )
    termination_b = tables.Column(linkify=True, verbose_name=_('Component B'))
    tags = columns.TagColumn(url_name='plugins:netbox_rack_concept:conceptcable_list')

    class Meta(NetBoxTable.Meta):
        model = ConceptCable
        fields = (
            'pk', 'id', 'label', 'concept', 'status', 'type', 'color', 'termination_a_device', 'termination_a',
            'termination_b_device', 'termination_b', 'description', 'tags', 'created', 'last_updated',
        )
        default_columns = (
            'id', 'concept', 'status', 'type', 'termination_a_device', 'termination_a', 'termination_b_device',
            'termination_b',
        )
