from django.conf import settings

from netbox.plugins import PluginTemplateExtension

from .models import RackConcept


def _enabled():
    return settings.PLUGINS_CONFIG.get('netbox_rack_concept', {}).get('enable_rack_tab', True)


class RackConceptButtons(PluginTemplateExtension):
    """
    Adds "Copy to concept" to the button row of a rack, "Merge into concept" to the
    rack list's toolbar, and lists concepts derived from a rack.
    """
    models = ['dcim.rack']

    def buttons(self):
        if not _enabled():
            return ''
        if not self.context['request'].user.has_perm('netbox_rack_concept.add_rackconcept'):
            return ''
        return self.render('netbox_rack_concept/inc/rack_copy_button.html', extra_context={
            'rack': self.context['object'],
        })

    def list_buttons(self):
        if not _enabled():
            return ''
        if not self.context['request'].user.has_perm('netbox_rack_concept.add_rackconcept'):
            return ''
        return self.render('netbox_rack_concept/inc/rack_list_merge_button.html')

    def right_page(self):
        if not _enabled():
            return ''
        rack = self.context['object']
        concepts = RackConcept.objects.restrict(self.context['request'].user, 'view').filter(source_rack=rack)
        if not concepts:
            return ''
        return self.render('netbox_rack_concept/inc/rack_concepts_panel.html', extra_context={
            'concepts': concepts,
        })


template_extensions = [RackConceptButtons]
