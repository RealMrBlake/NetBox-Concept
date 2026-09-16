from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from dcim.models import Rack
from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets
from .. import deploy as deploy_utils
from ..elevation import get_elevations
from ..models import ConceptDevice, RackConcept
from .serializers import (
    ConceptDeploySerializer, ConceptDeviceSerializer, RackConceptCloneSerializer, RackConceptSerializer,
    RackCopySerializer,
)

__all__ = (
    'ConceptDeviceViewSet',
    'RackConceptViewSet',
)


class RackConceptViewSet(NetBoxModelViewSet):
    queryset = RackConcept.objects.prefetch_related('tags').annotate(
        device_count=Count('devices')
    ).select_related('tenant', 'tenant_group', 'rack_type')
    serializer_class = RackConceptSerializer
    filterset_class = filtersets.RackConceptFilterSet

    @action(detail=False, methods=['post'], url_path='copy-from-rack')
    def copy_from_rack(self, request):
        """Create a concept from an existing rack, optionally including its devices."""
        serializer = RackCopySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        rack = get_object_or_404(Rack.objects.restrict(request.user, 'view'), pk=data['rack'].pk)
        tenant = data.get('tenant')

        try:
            concept = deploy_utils.copy_rack_to_concept(
                rack=rack,
                name=data['name'],
                status=data['status'],
                tenant=tenant,
                tenant_group=tenant.group if tenant else None,
                description=data['description'],
                include_devices=data['include_devices'],
                include_device_names=data['include_device_names'],
            )
        except ValidationError as exc:
            return Response({'errors': exc.message_dict if hasattr(exc, 'message_dict') else exc.messages},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(
            RackConceptSerializer(concept, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Duplicate this concept into a new one."""
        concept = self.get_object()
        serializer = RackConceptCloneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            new_concept = deploy_utils.clone_concept(
                concept=concept,
                name=data['name'],
                status=data['status'],
                tenant=data.get('tenant'),
                include_devices=data['include_devices'],
            )
        except ValidationError as exc:
            return Response({'errors': exc.message_dict if hasattr(exc, 'message_dict') else exc.messages},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(
            RackConceptSerializer(new_concept, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def deploy(self, request, pk=None):
        """
        Materialise this concept as one or more real racks. Pass dry_run=true to get the
        rack names and warnings back without writing anything.
        """
        concept = self.get_object()
        serializer = ConceptDeploySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not request.user.has_perm('dcim.add_rack'):
            return Response({'detail': 'Permission denied: dcim.add_rack'}, status=status.HTTP_403_FORBIDDEN)

        planned, warnings = deploy_utils.validate_deployment(
            concept, data['create_devices'], data['skip_unnamed_devices']
        )

        if data['dry_run']:
            return Response({
                'dry_run': True,
                'racks': data['rack_names'],
                'devices_per_rack': len(planned),
                'total_devices': len(planned) * len(data['rack_names']),
                'warnings': warnings,
            })

        try:
            racks, devices, warnings = deploy_utils.deploy_concept(
                concept=concept,
                rack_names=data['rack_names'],
                site=data['site'],
                location=data.get('location'),
                tenant=data.get('tenant'),
                create_devices=data['create_devices'],
                device_name_pattern=data['device_name_pattern'],
                skip_unnamed_devices=data['skip_unnamed_devices'],
                user=request.user,
            )
        except ValidationError as exc:
            return Response(
                {
                    'detail': 'Deployment failed; nothing was created.',
                    'errors': exc.message_dict if hasattr(exc, 'message_dict') else exc.messages,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'racks': [{'id': r.pk, 'name': r.name, 'url': r.get_absolute_url()} for r in racks],
            'device_count': len(devices),
            'warnings': warnings,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def elevation(self, request, pk=None):
        """The computed elevation geometry, for external renderers."""
        concept = self.get_object()
        front, rear = get_elevations(concept)
        return Response({
            'u_height': concept.u_height,
            'starting_unit': concept.starting_unit,
            'desc_units': concept.desc_units,
            'faces': {
                elevation.face: [
                    {
                        'device_id': block.device.pk,
                        'label': block.label,
                        'position': block.device.position,
                        'u_height': block.device.effective_u_height,
                        'width_fraction': block.device.width_fraction,
                        'horizontal_position': block.device.horizontal_position,
                        'mounted_on_opposite_face': block.opposite,
                        'color': block.color,
                    }
                    for block in elevation.blocks
                ]
                for elevation in (front, rear)
            },
        })


class ConceptDeviceViewSet(NetBoxModelViewSet):
    queryset = ConceptDevice.objects.prefetch_related('tags').select_related(
        'concept', 'device_type', 'device_type__manufacturer', 'role', 'platform', 'tenant'
    )
    serializer_class = ConceptDeviceSerializer
    filterset_class = filtersets.ConceptDeviceFilterSet
