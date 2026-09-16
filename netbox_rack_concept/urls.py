from django.urls import include, path

from utilities.urls import get_model_urls

from . import views

app_name = 'netbox_rack_concept'

urlpatterns = [
    # Rack concepts
    path('concepts/', include(get_model_urls('netbox_rack_concept', 'rackconcept', detail=False))),
    # Combine two concepts into a taller one. Listed before the <int:pk>/ include below only
    # for readability; 'merge' can never match the int converter anyway.
    path('concepts/merge/', views.MergeConceptsView.as_view(), name='rackconcept_merge'),
    path('concepts/<int:pk>/', include(get_model_urls('netbox_rack_concept', 'rackconcept'))),

    # Planned devices
    path('devices/', include(get_model_urls('netbox_rack_concept', 'conceptdevice', detail=False))),
    path('devices/<int:pk>/', include(get_model_urls('netbox_rack_concept', 'conceptdevice'))),

    # Components and cabling
    path('components/', include(get_model_urls('netbox_rack_concept', 'conceptcomponent', detail=False))),
    path('components/<int:pk>/', include(get_model_urls('netbox_rack_concept', 'conceptcomponent'))),
    path('cables/', include(get_model_urls('netbox_rack_concept', 'conceptcable', detail=False))),
    path('cables/<int:pk>/', include(get_model_urls('netbox_rack_concept', 'conceptcable'))),

    # Entry points from real racks
    path('racks/<int:pk>/copy/', views.RackCopyView.as_view(), name='rack_copy'),
    path('racks/merge/', views.MergeRacksToConceptView.as_view(), name='racks_merge'),
]
