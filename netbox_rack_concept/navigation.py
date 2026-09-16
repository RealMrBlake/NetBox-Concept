from django.utils.translation import gettext_lazy as _

from netbox.choices import ButtonColorChoices
from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

concept_buttons = [
    PluginMenuButton(
        link='plugins:netbox_rack_concept:rackconcept_add',
        title=_('Add'),
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN,
        permissions=['netbox_rack_concept.add_rackconcept']
    ),
    PluginMenuButton(
        link='plugins:netbox_rack_concept:rackconcept_bulk_import',
        title=_('Import'),
        icon_class='mdi mdi-upload',
        color=ButtonColorChoices.CYAN,
        permissions=['netbox_rack_concept.add_rackconcept']
    ),
    PluginMenuButton(
        link='plugins:netbox_rack_concept:rackconcept_merge',
        title=_('Merge'),
        icon_class='mdi mdi-call-merge',
        color=ButtonColorChoices.PURPLE,
        permissions=['netbox_rack_concept.add_rackconcept']
    ),
]

device_buttons = [
    PluginMenuButton(
        link='plugins:netbox_rack_concept:conceptdevice_add',
        title=_('Add'),
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN,
        permissions=['netbox_rack_concept.add_conceptdevice']
    ),
    PluginMenuButton(
        link='plugins:netbox_rack_concept:conceptdevice_bulk_import',
        title=_('Import'),
        icon_class='mdi mdi-upload',
        color=ButtonColorChoices.CYAN,
        permissions=['netbox_rack_concept.add_conceptdevice']
    ),
]

cable_buttons = [
    PluginMenuButton(
        link='plugins:netbox_rack_concept:conceptcable_add',
        title=_('Add'),
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN,
        permissions=['netbox_rack_concept.add_conceptcable']
    ),
]

menu = PluginMenu(
    label=_('Rack Concepts'),
    icon_class='mdi mdi-view-grid-plus-outline',
    groups=(
        (_('Planning'), (
            PluginMenuItem(
                link='plugins:netbox_rack_concept:rackconcept_list',
                link_text=_('Rack Concepts'),
                permissions=['netbox_rack_concept.view_rackconcept'],
                buttons=concept_buttons
            ),
            PluginMenuItem(
                link='plugins:netbox_rack_concept:conceptdevice_list',
                link_text=_('Planned Devices'),
                permissions=['netbox_rack_concept.view_conceptdevice'],
                buttons=device_buttons
            ),
        )),
        (_('Cabling'), (
            PluginMenuItem(
                link='plugins:netbox_rack_concept:conceptcomponent_list',
                link_text=_('Components'),
                permissions=['netbox_rack_concept.view_conceptcomponent'],
            ),
            PluginMenuItem(
                link='plugins:netbox_rack_concept:conceptcable_list',
                link_text=_('Cables'),
                permissions=['netbox_rack_concept.view_conceptcable'],
                buttons=cable_buttons
            ),
        )),
    )
)
