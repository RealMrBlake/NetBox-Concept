from netbox.plugins import PluginConfig

__version__ = '0.2.1'


class RackConceptConfig(PluginConfig):
    name = 'netbox_rack_concept'
    verbose_name = 'NetBox Rack Concepts'
    description = 'Rack blueprints: plan racks and their equipment without creating real racks or devices'
    version = __version__
    author = 'Claude'
    base_url = 'rack-concepts'
    min_version = '4.6.0'
    max_version = '4.6.99'
    # These paths are relative to this module (NetBox prepends self.__module__),
    # so they must NOT be prefixed with 'netbox_rack_concept.' again.
    menu = 'navigation.menu'
    template_extensions = 'template_content.template_extensions'

    default_settings = {
        # Defaults used when a concept is created from scratch.
        'default_u_height': 42,
        'default_width': 19,

        # Show the "Copy to concept" button on the dcim.Rack detail page.
        'enable_rack_tab': True,

        # Status assigned to the objects created when a concept is deployed.
        'deployed_rack_status': 'planned',
        'deployed_device_status': 'planned',

        # Mapping onto the partial-width implementation of netbox_utilities.
        # Adjust these if that plugin renames its fields; set 'enabled' to False
        # to never write partial-width data during deployment.
        'partial_width': {
            'enabled': True,
            'model': 'netbox_utilities.RackDevicePosition',
            'device_field': 'device',
            'fraction_field': 'width_fraction',
            'position_field': 'horizontal_position',
        },
    }

    def ready(self):
        super().ready()
        from . import search  # noqa: F401


config = RackConceptConfig
