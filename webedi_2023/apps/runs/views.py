from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from spices.services import ServiceClientError

from apps.adapters.engine import post_process_discovered_files
from apps.jobconfig.views import AccountAuthenticatedApiView
from apps.runs.models import Run, DiscoveredFile, RunStatus
from apps.runs.serializers import RunSerializer, DiscoveredFileSerializer


class RunViewSet(AccountAuthenticatedApiView, viewsets.ReadOnlyModelViewSet):
    serializer_class = RunSerializer
    filterset_fields = (
        "status",
        "job__connector_id",
        "job_id",
        "job__account_id",
    )
    ordering_fields = ("id", "execution_start_ts", "execution_end_ts", "status")
    ordering = ("-id",)
    acl_field = "job__account"

    queryset = (
        Run.objects.all()
        .select_related(
            "job",
            "job__connector",
            "job__connector__connector_vendor",
        )
        .prefetch_related("job__piq_mappings", "job__connector__capabilities")
    )

    @action(
        detail=True, methods=["POST"], url_path="post-process", url_name="post-process"
    )
    def run_post_process_file_action(
        self, request, pk
    ):  # pylint: disable=unused-argument
        run: Run = self.get_object()
        if run.status != RunStatus.SUCCEEDED.ident:  # pylint: disable=no-member
            raise ServiceClientError(
                http_status_code=status.HTTP_412_PRECONDITION_FAILED,
                code="RUN_STATUS_NOT_SUCCESS",
                message=f"Run status must be  success ({RunStatus.SUCCEEDED}) to for post processing",
            )
        post_process_discovered_files(run)
        return Response(status=status.HTTP_200_OK)


class DiscoveredFileViewSet(AccountAuthenticatedApiView, viewsets.ReadOnlyModelViewSet):
    serializer_class = DiscoveredFileSerializer
    ordering = ("id",)
    acl_field = "run__job__account"

    def get_queryset(self):
        queryset = DiscoveredFile.objects.filter(
            run=self.kwargs["run_id"]
        ).prefetch_related(
            "run",
            "connector",
        )
        return queryset
