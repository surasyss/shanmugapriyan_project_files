from rest_framework.routers import DefaultRouter

from apps.jobconfig.views import (
    JobViewSet,
    JobPIQMappingViewSet,
    ConnectorRequestViewSet,
    JobScheduleViewSet,
)

jobconfig_router = DefaultRouter()

jobconfig_router.register(r"job", JobViewSet, basename="job")
jobconfig_router.register(
    r"job/(?P<job_id>.+)/piq-mappings",
    JobPIQMappingViewSet,
    basename="job-piq_mappings",
)
jobconfig_router.register(
    r"connectorrequest", ConnectorRequestViewSet, basename="connectorrequest"
)

jobconfig_router.register(r"schedule", JobScheduleViewSet, basename="schedule")
