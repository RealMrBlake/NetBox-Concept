from netbox.api.routers import NetBoxRouter

from . import views

app_name = 'netbox_rack_concept-api'

router = NetBoxRouter()
router.register('concepts', views.RackConceptViewSet)
router.register('devices', views.ConceptDeviceViewSet)

urlpatterns = router.urls
