from django.utils.translation import gettext_lazy as _

from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem
from utilities.choices import ButtonColorChoices

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
    )
)
