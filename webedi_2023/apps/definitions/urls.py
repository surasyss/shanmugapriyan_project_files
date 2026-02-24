from rest_framework.routers import DefaultRouter

from apps.definitions.views import ConnectorViewSet

definitions_router = DefaultRouter()

definitions_router.register(r"connector", ConnectorViewSet, basename="connector")
