import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views.generic import View

from dcim.choices import DeviceFaceChoices
from dcim.models import Rack
from netbox.views import generic
from utilities.views import ObjectPermissionRequiredMixin, ViewTab, register_model_view

from . import components, deploy, filtersets, forms, tables
from .choices import ConceptComponentTypeChoices
from .drawio import build_drawio
from .elevation import get_elevations
from .models import ConceptCable, ConceptComponent, ConceptDevice, RackConcept

__all__ = (
    'ConceptCableView',
    'ConceptComponentView',
    'ConceptDeviceView',
    'MergeConceptsView',
    'MergeRacksToConceptView',
    'RackConceptView',
)


#
# Rack concepts
#

@register_model_view(RackConcept, 'list', path='', detail=False)
class RackConceptListView(generic.ObjectListView):
    queryset = RackConcept.objects.annotate(
        device_count=Count('devices')
    ).select_related('tenant', 'tenant_group', 'rack_type')
    table = tables.RackConceptTable
    filterset = filtersets.RackConceptFilterSet
    filterset_form = forms.RackConceptFilterForm


@register_model_view(RackConcept)
class RackConceptView(generic.ObjectView):
    queryset = RackConcept.objects.select_related('tenant', 'tenant_group', 'rack_type', 'source_rack')
    template_name = 'netbox_rack_concept/rackconcept.html'

    def get_extra_context(self, request, instance):
        front, rear = get_elevations(instance)
        deployments = tables.ConceptDeploymentTable(
            instance.deployments.select_related('rack', 'user')
        )
        return {
            'front_elevation': front,
            'rear_elevation': rear,
            'deployments_table': deployments,
        }


@register_model_view(RackConcept, 'export_svg', path='export/svg')
class RackConceptExportSVGView(ObjectPermissionRequiredMixin, View):
    """Download one face's elevation as a standalone SVG file."""
    queryset = RackConcept.objects.all()

    def get_required_permission(self):
        return 'netbox_rack_concept.view_rackconcept'

    def get(self, request, pk):
        concept = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)
        face = request.GET.get('face')
        if face not in (DeviceFaceChoices.FACE_FRONT, DeviceFaceChoices.FACE_REAR):
            face = DeviceFaceChoices.FACE_FRONT

        front, rear = get_elevations(concept)
        elevation = front if face == DeviceFaceChoices.FACE_FRONT else rear

        svg = render_to_string('netbox_rack_concept/elevation_export.html', {'elevation': elevation}, request=request)
        response = HttpResponse(svg, content_type='image/svg+xml')
        response['Content-Disposition'] = f'attachment; filename="{slugify(concept.name)}-{face}.svg"'
        return response


@register_model_view(RackConcept, 'export_data', path='export/data')
class RackConceptExportDataView(ObjectPermissionRequiredMixin, View):
    """
    The elevation's full pixel geometry as JSON, for the PNG export: it draws straight
    onto a <canvas> from this rather than rasterizing an SVG image, so a device type
    image only ever reaches the canvas via a same-origin fetch()->blob()->Image, never
    through an <img src="blob:svg..."> whose validity (and therefore whether it even
    decodes) depends on the SVG being perfectly well-formed.
    """
    queryset = RackConcept.objects.all()

    def get_required_permission(self):
        return 'netbox_rack_concept.view_rackconcept'

    def get(self, request, pk):
        concept = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)
        front, rear = get_elevations(concept)

        def serialize(elevation):
            return {
                'width': elevation.width,
                'height': elevation.height,
                'rack_x': elevation.rack_x,
                'rack_width': elevation.rack_width,
                'face_label': elevation.face_label.title(),
                'units': [
                    {'number': unit.number, 'y': unit.y, 'height': unit.height}
                    for unit in elevation.units
                ],
                'blocks': [
                    {
                        'x': block.x,
                        'y': block.y,
                        'width': block.width,
                        'height': block.height,
                        'color': block.color,
                        'text_color': block.text_color,
                        'label': block.label,
                        'opposite': block.opposite,
                        'show_text': block.show_text,
                        'image_url': (
                            request.build_absolute_uri(block.image.url) if block.image else None
                        ),
                    }
                    for block in elevation.blocks
                ],
            }

        return JsonResponse({
            'name': concept.name,
            'front': serialize(front),
            'rear': serialize(rear),
        })


@register_model_view(RackConcept, 'export_drawio', path='export/drawio')
class RackConceptExportDrawioView(ObjectPermissionRequiredMixin, View):
    """Download both faces of a concept as one draw.io (diagrams.net) diagram."""
    queryset = RackConcept.objects.all()

    def get_required_permission(self):
        return 'netbox_rack_concept.view_rackconcept'

    def get(self, request, pk):
        concept = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)
        xml = build_drawio(concept)
        response = HttpResponse(xml, content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename="{slugify(concept.name)}.drawio"'
        return response


@register_model_view(RackConcept, 'devices')
class RackConceptDevicesView(generic.ObjectChildrenView):
    queryset = RackConcept.objects.all()
    child_model = ConceptDevice
    table = tables.ConceptDeviceElevationTable
    filterset = filtersets.ConceptDeviceFilterSet
    template_name = 'netbox_rack_concept/rackconcept_devices.html'
    tab = ViewTab(
        label=_('Devices'),
        badge=lambda obj: obj.devices.count(),
        permission='netbox_rack_concept.view_conceptdevice',
        weight=500
    )

    def get_children(self, request, parent):
        return parent.devices.select_related('device_type', 'device_type__manufacturer', 'role', 'platform', 'tenant')


@register_model_view(RackConcept, 'add', detail=False)
@register_model_view(RackConcept, 'edit')
class RackConceptEditView(generic.ObjectEditView):
    queryset = RackConcept.objects.all()
    form = forms.RackConceptForm

    def alter_object(self, obj, request, url_args, url_kwargs):
        if not obj.pk:
            config = settings.PLUGINS_CONFIG.get('netbox_rack_concept', {})
            obj.u_height = config.get('default_u_height', 42)
            obj.width = config.get('default_width', 19)
        return obj


@register_model_view(RackConcept, 'delete')
class RackConceptDeleteView(generic.ObjectDeleteView):
    queryset = RackConcept.objects.all()


@register_model_view(RackConcept, 'bulk_import', path='import', detail=False)
class RackConceptBulkImportView(generic.BulkImportView):
    queryset = RackConcept.objects.all()
    model_form = forms.RackConceptImportForm


@register_model_view(RackConcept, 'bulk_edit', path='edit', detail=False)
class RackConceptBulkEditView(generic.BulkEditView):
    queryset = RackConcept.objects.annotate(device_count=Count('devices'))
    filterset = filtersets.RackConceptFilterSet
    table = tables.RackConceptTable
    form = forms.RackConceptBulkEditForm


@register_model_view(RackConcept, 'bulk_delete', path='delete', detail=False)
class RackConceptBulkDeleteView(generic.BulkDeleteView):
    queryset = RackConcept.objects.annotate(device_count=Count('devices'))
    filterset = filtersets.RackConceptFilterSet
    table = tables.RackConceptTable


#
# Concept devices
#

@register_model_view(ConceptDevice, 'list', path='', detail=False)
class ConceptDeviceListView(generic.ObjectListView):
    queryset = ConceptDevice.objects.select_related(
        'concept', 'device_type', 'device_type__manufacturer', 'role', 'platform', 'tenant'
    )
    table = tables.ConceptDeviceTable
    filterset = filtersets.ConceptDeviceFilterSet
    filterset_form = forms.ConceptDeviceFilterForm


@register_model_view(ConceptDevice)
class ConceptDeviceView(generic.ObjectView):
    queryset = ConceptDevice.objects.select_related(
        'concept', 'device_type', 'device_type__manufacturer', 'role', 'platform', 'tenant', 'source_device'
    )
    template_name = 'netbox_rack_concept/conceptdevice.html'


@register_model_view(ConceptDevice, 'sync_components')
class ConceptDeviceSyncComponentsView(ObjectPermissionRequiredMixin, View):
    """Populate a device's components from its device type's templates."""
    queryset = ConceptDevice.objects.all()

    def get_required_permission(self):
        return 'netbox_rack_concept.add_conceptcomponent'

    def get(self, request, pk):
        device = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)
        return render(request, 'netbox_rack_concept/conceptdevice_sync_components.html', {
            'object': device,
            'return_url': device.get_absolute_url(),
        })

    def post(self, request, pk):
        device = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)

        if device.device_type is None:
            messages.error(request, _('%(device)s has no device type to sync components from.') % {'device': device})
            return redirect(device.get_absolute_url())

        created, mapped = components.sync_components(device)
        if created:
            messages.success(request, _('Created %(count)s component(s).') % {'count': created})
        else:
            messages.info(request, _('No new components to create; everything is already in sync.'))
        if mapped:
            messages.success(request, _('Mapped %(count)s front/rear port pair(s).') % {'count': mapped})

        return redirect(device.get_absolute_url())


class ConceptDeviceComponentsView(generic.ObjectChildrenView):
    """
    Base for the per-type component tabs (Interfaces / Front Ports / ...), mirroring
    dcim's own device component tabs one-for-one: same names, paths and tab order.
    Since one ConceptComponent model covers every type (see models.py), a subclass only
    needs to say which component_type it shows - there's no separate model per tab to
    plug in the way dcim.Interface/dcim.FrontPort/etc. do.
    """
    queryset = ConceptDevice.objects.all()
    child_model = ConceptComponent
    table = tables.ConceptComponentTable
    filterset = filtersets.ConceptComponentFilterSet
    filterset_form = forms.ConceptComponentFilterForm
    template_name = 'netbox_rack_concept/conceptdevice_components.html'
    component_type = None

    def get_children(self, request, parent):
        return ConceptComponent.objects.restrict(request.user, 'view').filter(
            device=parent, component_type=self.component_type
        )

    def get_table(self, data, request, bulk_actions=True):
        # device/concept/component_type are all implied by "which tab this is" - showing
        # them again on every row would just be noise.
        table = self.table(data, exclude=('device', 'concept', 'component_type'))
        if 'pk' in table.base_columns and bulk_actions:
            table.columns.show('pk')
        table.configure(request)
        return table

    def get_extra_context(self, request, instance):
        return {
            'component_type': self.component_type,
            'component_type_label': self.tab.label,
        }


@register_model_view(ConceptDevice, 'consoleports', path='console-ports')
class ConceptDeviceConsolePortsView(ConceptDeviceComponentsView):
    component_type = ConceptComponentTypeChoices.TYPE_CONSOLE_PORT
    tab = ViewTab(
        label=_('Console Ports'),
        badge=lambda obj: obj.components.filter(component_type=ConceptComponentTypeChoices.TYPE_CONSOLE_PORT).count(),
        permission='netbox_rack_concept.view_conceptcomponent',
        weight=550,
        hide_if_empty=True
    )


@register_model_view(ConceptDevice, 'consoleserverports', path='console-server-ports')
class ConceptDeviceConsoleServerPortsView(ConceptDeviceComponentsView):
    component_type = ConceptComponentTypeChoices.TYPE_CONSOLE_SERVER_PORT
    tab = ViewTab(
        label=_('Console Server Ports'),
        badge=lambda obj: obj.components.filter(
            component_type=ConceptComponentTypeChoices.TYPE_CONSOLE_SERVER_PORT
        ).count(),
        permission='netbox_rack_concept.view_conceptcomponent',
        weight=560,
        hide_if_empty=True
    )


@register_model_view(ConceptDevice, 'powerports', path='power-ports')
class ConceptDevicePowerPortsView(ConceptDeviceComponentsView):
    component_type = ConceptComponentTypeChoices.TYPE_POWER_PORT
    tab = ViewTab(
        label=_('Power Ports'),
        badge=lambda obj: obj.components.filter(component_type=ConceptComponentTypeChoices.TYPE_POWER_PORT).count(),
        permission='netbox_rack_concept.view_conceptcomponent',
        weight=570,
        hide_if_empty=True
    )


@register_model_view(ConceptDevice, 'poweroutlets', path='power-outlets')
class ConceptDevicePowerOutletsView(ConceptDeviceComponentsView):
    component_type = ConceptComponentTypeChoices.TYPE_POWER_OUTLET
    tab = ViewTab(
        label=_('Power Outlets'),
        badge=lambda obj: obj.components.filter(component_type=ConceptComponentTypeChoices.TYPE_POWER_OUTLET).count(),
        permission='netbox_rack_concept.view_conceptcomponent',
        weight=580,
        hide_if_empty=True
    )


@register_model_view(ConceptDevice, 'interfaces')
class ConceptDeviceInterfacesView(ConceptDeviceComponentsView):
    component_type = ConceptComponentTypeChoices.TYPE_INTERFACE
    tab = ViewTab(
        label=_('Interfaces'),
        badge=lambda obj: obj.components.filter(component_type=ConceptComponentTypeChoices.TYPE_INTERFACE).count(),
        permission='netbox_rack_concept.view_conceptcomponent',
        weight=520,
        hide_if_empty=True
    )


@register_model_view(ConceptDevice, 'frontports', path='front-ports')
class ConceptDeviceFrontPortsView(ConceptDeviceComponentsView):
    component_type = ConceptComponentTypeChoices.TYPE_FRONT_PORT
    tab = ViewTab(
        label=_('Front Ports'),
        badge=lambda obj: obj.components.filter(component_type=ConceptComponentTypeChoices.TYPE_FRONT_PORT).count(),
        permission='netbox_rack_concept.view_conceptcomponent',
        weight=530,
        hide_if_empty=True
    )


@register_model_view(ConceptDevice, 'rearports', path='rear-ports')
class ConceptDeviceRearPortsView(ConceptDeviceComponentsView):
    component_type = ConceptComponentTypeChoices.TYPE_REAR_PORT
    tab = ViewTab(
        label=_('Rear Ports'),
        badge=lambda obj: obj.components.filter(component_type=ConceptComponentTypeChoices.TYPE_REAR_PORT).count(),
        permission='netbox_rack_concept.view_conceptcomponent',
        weight=540,
        hide_if_empty=True
    )


@register_model_view(ConceptDevice, 'add', detail=False)
@register_model_view(ConceptDevice, 'edit')
class ConceptDeviceEditView(generic.ObjectEditView):
    queryset = ConceptDevice.objects.all()
    form = forms.ConceptDeviceForm


@register_model_view(ConceptDevice, 'delete')
class ConceptDeviceDeleteView(generic.ObjectDeleteView):
    queryset = ConceptDevice.objects.all()


@register_model_view(ConceptDevice, 'bulk_import', path='import', detail=False)
class ConceptDeviceBulkImportView(generic.BulkImportView):
    queryset = ConceptDevice.objects.all()
    model_form = forms.ConceptDeviceImportForm


@register_model_view(ConceptDevice, 'bulk_edit', path='edit', detail=False)
class ConceptDeviceBulkEditView(generic.BulkEditView):
    queryset = ConceptDevice.objects.select_related('concept', 'device_type', 'role')
    filterset = filtersets.ConceptDeviceFilterSet
    table = tables.ConceptDeviceTable
    form = forms.ConceptDeviceBulkEditForm


@register_model_view(ConceptDevice, 'bulk_delete', path='delete', detail=False)
class ConceptDeviceBulkDeleteView(generic.BulkDeleteView):
    queryset = ConceptDevice.objects.select_related('concept', 'device_type', 'role')
    filterset = filtersets.ConceptDeviceFilterSet
    table = tables.ConceptDeviceTable


#
# Actions: copy, clone, deploy, reorder
#

class RackCopyView(ObjectPermissionRequiredMixin, View):
    """Copy a real rack into a new concept. Reached from the rack detail page."""
    queryset = RackConcept.objects.all()

    def get_required_permission(self):
        return 'netbox_rack_concept.add_rackconcept'

    def get(self, request, pk):
        rack = get_object_or_404(Rack.objects.restrict(request.user, 'view'), pk=pk)
        form = forms.RackCopyForm(initial={
            'name': _('%(rack)s (concept)') % {'rack': rack.name},
            'tenant': rack.tenant_id,
            'tenant_group': rack.tenant.group_id if rack.tenant else None,
        })
        return render(request, 'netbox_rack_concept/rack_copy.html', {
            'rack': rack,
            'form': form,
            'device_count': rack.devices.filter(position__isnull=False).count(),
            'return_url': rack.get_absolute_url(),
        })

    def post(self, request, pk):
        rack = get_object_or_404(Rack.objects.restrict(request.user, 'view'), pk=pk)
        form = forms.RackCopyForm(request.POST)

        if form.is_valid():
            try:
                concept, warnings, cable_summary = deploy.copy_rack_to_concept(
                    rack=rack,
                    name=form.cleaned_data['name'],
                    status=form.cleaned_data['status'],
                    tenant=form.cleaned_data['tenant'],
                    tenant_group=form.cleaned_data['tenant_group'],
                    description=form.cleaned_data['description'],
                    include_devices=form.cleaned_data['include_devices'],
                    include_device_names=form.cleaned_data['include_device_names'],
                    override_width=form.cleaned_data['override_width'],
                    override_u_height=form.cleaned_data['override_u_height'],
                    override_starting_unit=form.cleaned_data['override_starting_unit'],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                for warning in warnings:
                    messages.warning(request, warning)
                if cable_summary['skipped']:
                    messages.warning(request, _(
                        '%(count)s cable(s) could not be copied because they reach outside the rack or use more '
                        'than one termination per side.'
                    ) % {'count': cable_summary['skipped']})
                success_message = _('Created concept %(concept)s from rack %(rack)s.') % {
                    'concept': concept, 'rack': rack
                }
                if cable_summary['copied']:
                    success_message += ' ' + _('Copied %(count)s cable(s).') % {'count': cable_summary['copied']}
                messages.success(request, success_message)
                return redirect(concept.get_absolute_url())

        return render(request, 'netbox_rack_concept/rack_copy.html', {
            'rack': rack,
            'form': form,
            'device_count': rack.devices.filter(position__isnull=False).count(),
            'return_url': rack.get_absolute_url(),
        })


class MergeConceptsView(ObjectPermissionRequiredMixin, View):
    """Stack two blueprints (e.g. two half-height racks) into one taller concept."""
    queryset = RackConcept.objects.all()

    def get_required_permission(self):
        return 'netbox_rack_concept.add_rackconcept'

    def get(self, request):
        form = forms.MergeConceptsForm(initial={
            'concept_bottom': request.GET.get('concept_bottom'),
            'concept_top': request.GET.get('concept_top'),
        })
        return render(request, 'netbox_rack_concept/concept_merge.html', {
            'form': form,
            'return_url': reverse('plugins:netbox_rack_concept:rackconcept_list'),
        })

    def post(self, request):
        form = forms.MergeConceptsForm(request.POST)

        if form.is_valid():
            try:
                merged, warnings = deploy.merge_concepts(
                    concept_bottom=form.cleaned_data['concept_bottom'],
                    concept_top=form.cleaned_data['concept_top'],
                    name=form.cleaned_data['name'],
                    status=form.cleaned_data['status'],
                    tenant=form.cleaned_data['tenant'],
                    tenant_group=form.cleaned_data['tenant_group'],
                    width=form.cleaned_data['width'],
                    u_height=form.cleaned_data['u_height'],
                    starting_unit=form.cleaned_data['starting_unit'],
                    description=form.cleaned_data['description'],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                for warning in warnings:
                    messages.warning(request, warning)
                messages.success(request, _('Created %(merged)s by merging %(bottom)s and %(top)s.') % {
                    'merged': merged,
                    'bottom': form.cleaned_data['concept_bottom'],
                    'top': form.cleaned_data['concept_top'],
                })
                return redirect(merged.get_absolute_url())

        return render(request, 'netbox_rack_concept/concept_merge.html', {
            'form': form,
            'return_url': reverse('plugins:netbox_rack_concept:rackconcept_list'),
        })


class MergeRacksToConceptView(ObjectPermissionRequiredMixin, View):
    """Combine two real racks directly into one new, stacked blueprint."""
    queryset = RackConcept.objects.all()

    def get_required_permission(self):
        return 'netbox_rack_concept.add_rackconcept'

    def get(self, request):
        form = forms.MergeRacksForm(initial={
            'rack_bottom': request.GET.get('rack_bottom'),
            'rack_top': request.GET.get('rack_top'),
        })
        return render(request, 'netbox_rack_concept/racks_merge.html', {
            'form': form,
            'return_url': reverse('dcim:rack_list'),
        })

    def post(self, request):
        form = forms.MergeRacksForm(request.POST)

        if form.is_valid():
            try:
                concept, warnings, cable_summary = deploy.merge_racks_to_concept(
                    rack_bottom=form.cleaned_data['rack_bottom'],
                    rack_top=form.cleaned_data['rack_top'],
                    name=form.cleaned_data['name'],
                    status=form.cleaned_data['status'],
                    tenant=form.cleaned_data['tenant'],
                    tenant_group=form.cleaned_data['tenant_group'],
                    include_devices=form.cleaned_data['include_devices'],
                    include_device_names=form.cleaned_data['include_device_names'],
                    width=form.cleaned_data['width'],
                    u_height=form.cleaned_data['u_height'],
                    starting_unit=form.cleaned_data['starting_unit'],
                    description=form.cleaned_data['description'],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                for warning in warnings:
                    messages.warning(request, warning)
                if cable_summary['skipped']:
                    messages.warning(request, _(
                        '%(count)s cable(s) could not be copied because they reach outside the two racks or use '
                        'more than one termination per side.'
                    ) % {'count': cable_summary['skipped']})
                success_message = _('Created concept %(concept)s from %(bottom)s and %(top)s.') % {
                    'concept': concept,
                    'bottom': form.cleaned_data['rack_bottom'],
                    'top': form.cleaned_data['rack_top'],
                }
                if cable_summary['copied']:
                    success_message += ' ' + _('Copied %(count)s cable(s).') % {'count': cable_summary['copied']}
                messages.success(request, success_message)
                return redirect(concept.get_absolute_url())

        return render(request, 'netbox_rack_concept/racks_merge.html', {
            'form': form,
            'return_url': reverse('dcim:rack_list'),
        })


@register_model_view(RackConcept, 'clone_concept', path='clone')
class RackConceptCloneView(ObjectPermissionRequiredMixin, View):
    """Duplicate a concept to build a variant."""
    queryset = RackConcept.objects.all()

    def get_required_permission(self):
        return 'netbox_rack_concept.add_rackconcept'

    def get(self, request, pk):
        concept = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)
        form = forms.RackConceptCloneForm(initial={
            'name': _('%(name)s (copy)') % {'name': concept.name},
            'tenant': concept.tenant_id,
        })
        return render(request, 'netbox_rack_concept/concept_clone.html', {
            'object': concept,
            'form': form,
            'return_url': concept.get_absolute_url(),
        })

    def post(self, request, pk):
        concept = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)
        form = forms.RackConceptCloneForm(request.POST)

        if form.is_valid():
            try:
                clone = deploy.clone_concept(
                    concept=concept,
                    name=form.cleaned_data['name'],
                    status=form.cleaned_data['status'],
                    tenant=form.cleaned_data['tenant'],
                    include_devices=form.cleaned_data['include_devices'],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, _('Cloned %(source)s into %(clone)s.') % {
                    'source': concept, 'clone': clone
                })
                return redirect(clone.get_absolute_url())

        return render(request, 'netbox_rack_concept/concept_clone.html', {
            'object': concept,
            'form': form,
            'return_url': concept.get_absolute_url(),
        })


@register_model_view(RackConcept, 'deploy')
class RackConceptDeployView(ObjectPermissionRequiredMixin, View):
    """Materialise a concept as one or more real racks."""
    queryset = RackConcept.objects.all()

    def get_required_permission(self):
        # The mixin restricts against this view's queryset, so it has to be a concept
        # permission. The permission to create racks is checked separately below.
        return 'netbox_rack_concept.view_rackconcept'

    def _context(self, request, concept, form):
        # An unchecked checkbox is simply absent from the POST data.
        create_devices = 'create_devices' in form.data if form.is_bound else True
        deployable, warnings = deploy.validate_deployment(concept, create_devices=create_devices)
        return {
            'object': concept,
            'form': form,
            'deployable_count': len(deployable),
            'warnings': warnings,
            'return_url': concept.get_absolute_url(),
        }

    def get(self, request, pk):
        concept = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)
        form = forms.ConceptDeployForm(concept=concept)
        return render(request, 'netbox_rack_concept/concept_deploy.html', self._context(request, concept, form))

    def post(self, request, pk):
        concept = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)
        form = forms.ConceptDeployForm(request.POST, concept=concept)

        if not request.user.has_perm('dcim.add_rack'):
            return HttpResponseForbidden(_('You do not have permission to create racks.'))

        if form.is_valid():
            try:
                racks, devices, warnings = deploy.deploy_concept(
                    concept=concept,
                    rack_names=form.cleaned_data['rack_names'],
                    site=form.cleaned_data['site'],
                    location=form.cleaned_data['location'],
                    tenant=form.cleaned_data['tenant'],
                    create_devices=form.cleaned_data['create_devices'],
                    device_name_pattern=form.cleaned_data['device_name_pattern'],
                    skip_unnamed_devices=form.cleaned_data['skip_unnamed_devices'],
                    user=request.user,
                )
            except ValidationError as exc:
                # Nothing was written: deploy_concept runs in a transaction.
                messages.error(request, _('Deployment failed, nothing was created.'))
                form.add_error(None, exc)
            else:
                for warning in warnings:
                    messages.warning(request, warning)
                messages.success(request, _('Created %(racks)s rack(s) and %(devices)s device(s).') % {
                    'racks': len(racks), 'devices': len(devices)
                })
                if len(racks) == 1:
                    return redirect(racks[0].get_absolute_url())
                return redirect(
                    reverse('dcim:rack_list') + f'?site_id={form.cleaned_data["site"].pk}'
                )

        return render(request, 'netbox_rack_concept/concept_deploy.html', self._context(request, concept, form))


@register_model_view(RackConcept, 'reorder')
class RackConceptReorderView(ObjectPermissionRequiredMixin, View):
    """
    Endpoint for the drag & drop elevation. Accepts a JSON body of the shape
    {"devices": [{"id": 1, "position": "12.0", "face": "front", "horizontal_position": 0}]}
    and applies all moves in one transaction so a rejected move leaves nothing half-applied.
    """
    queryset = RackConcept.objects.all()
    http_method_names = ['post']

    def get_required_permission(self):
        return 'netbox_rack_concept.change_conceptdevice'

    def post(self, request, pk):
        concept = get_object_or_404(self.queryset.restrict(request.user, 'view'), pk=pk)

        try:
            payload = json.loads(request.body or '{}')
            moves = payload['devices']
        except (json.JSONDecodeError, KeyError, TypeError):
            return JsonResponse({'error': _('Malformed request body.')}, status=400)

        by_pk = {d.pk: d for d in concept.devices.select_related('device_type')}
        updated = []

        try:
            with transaction.atomic():
                for move in moves:
                    device = by_pk.get(int(move['id']))
                    if device is None:
                        raise ValidationError(_('Device %(id)s does not belong to this concept.') % {'id': move['id']})
                    try:
                        device.position = Decimal(str(move['position'])) if move.get('position') is not None else None
                    except InvalidOperation:
                        raise ValidationError(_('Invalid position %(position)r.') % {'position': move.get('position')})
                    if 'face' in move:
                        device.face = move['face']
                    if 'horizontal_position' in move:
                        device.horizontal_position = int(move['horizontal_position'])
                    if 'width_fraction' in move:
                        device.width_fraction = int(move['width_fraction'])
                    updated.append(device)

                # Validate only after every move is staged, so swapping two devices works.
                for device in updated:
                    device.save()
                for device in updated:
                    device.full_clean()
        except ValidationError as exc:
            return JsonResponse({'error': ' '.join(exc.messages)}, status=400)

        return JsonResponse({'status': 'ok', 'updated': len(updated)})


#
# Concept components
#

@register_model_view(ConceptComponent, 'list', path='', detail=False)
class ConceptComponentListView(generic.ObjectListView):
    queryset = ConceptComponent.objects.select_related('device', 'device__concept')
    table = tables.ConceptComponentTable
    filterset = filtersets.ConceptComponentFilterSet
    filterset_form = forms.ConceptComponentFilterForm


@register_model_view(ConceptComponent)
class ConceptComponentView(generic.ObjectView):
    queryset = ConceptComponent.objects.select_related('device', 'device__concept')
    template_name = 'netbox_rack_concept/conceptcomponent.html'

    def get_extra_context(self, request, instance):
        return {
            'paired_components': instance.get_paired_components(),
            'cable': instance.cable,
        }


@register_model_view(ConceptComponent, 'add', detail=False)
@register_model_view(ConceptComponent, 'edit')
class ConceptComponentEditView(generic.ObjectEditView):
    queryset = ConceptComponent.objects.all()
    form = forms.ConceptComponentForm


@register_model_view(ConceptComponent, 'delete')
class ConceptComponentDeleteView(generic.ObjectDeleteView):
    queryset = ConceptComponent.objects.all()


@register_model_view(ConceptComponent, 'bulk_delete', path='delete', detail=False)
class ConceptComponentBulkDeleteView(generic.BulkDeleteView):
    queryset = ConceptComponent.objects.select_related('device')
    filterset = filtersets.ConceptComponentFilterSet
    table = tables.ConceptComponentTable


#
# Concept cables
#

@register_model_view(ConceptCable, 'list', path='', detail=False)
class ConceptCableListView(generic.ObjectListView):
    queryset = ConceptCable.objects.select_related(
        'termination_a', 'termination_a__device', 'termination_b', 'termination_b__device'
    )
    table = tables.ConceptCableTable
    filterset = filtersets.ConceptCableFilterSet
    filterset_form = forms.ConceptCableFilterForm


@register_model_view(ConceptCable)
class ConceptCableView(generic.ObjectView):
    queryset = ConceptCable.objects.select_related(
        'termination_a', 'termination_a__device', 'termination_b', 'termination_b__device'
    )
    template_name = 'netbox_rack_concept/conceptcable.html'


@register_model_view(ConceptCable, 'add', detail=False)
@register_model_view(ConceptCable, 'edit')
class ConceptCableEditView(generic.ObjectEditView):
    queryset = ConceptCable.objects.all()
    form = forms.ConceptCableForm


@register_model_view(ConceptCable, 'delete')
class ConceptCableDeleteView(generic.ObjectDeleteView):
    queryset = ConceptCable.objects.all()


@register_model_view(ConceptCable, 'bulk_delete', path='delete', detail=False)
class ConceptCableBulkDeleteView(generic.BulkDeleteView):
    queryset = ConceptCable.objects.select_related('termination_a', 'termination_b')
    filterset = filtersets.ConceptCableFilterSet
    table = tables.ConceptCableTable
