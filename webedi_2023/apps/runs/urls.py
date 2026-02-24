from rest_framework.routers import DefaultRouter

from apps.runs.views import RunViewSet, DiscoveredFileViewSet

runs_router = DefaultRouter()

runs_router.register(r"run", RunViewSet, basename="run")
runs_router.register(
    r"run/(?P<run_id>.+)/discoveredfile",
    DiscoveredFileViewSet,
    basename="discoveredfile",
)
