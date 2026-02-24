from distutils.util import strtobool

from django.db.models import Q
from rest_framework import viewsets

from apps.definitions.models import Connector
from apps.definitions.serializers import ConnectorSerializer


class ConnectorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConnectorSerializer
    filterset_fields = ("type",)
    ordering_fields = ("name",)
    ordering = ("name",)

    def get_queryset(self):
        queryset = (
            Connector.objects.all()
            .exclude(adapter_code="backlog")
            .prefetch_related("connector_vendor", "capabilities")
        )

        enabled = self.request.query_params.get("enabled", None)
        adapter_code = self.request.query_params.get("adapter_code", None)
        name_search_string = self.request.query_params.get("name", None)
        show_hidden = self.request.query_params.get("show_hidden", "False")
        entity_type = self.request.query_params.get("entity_type", None)
        capability = self.request.query_params.get("capability", None)
        supports_import = self.request.query_params.get("supports_import", None)

        filter_qs = Q()

        if enabled:
            filter_qs &= Q(enabled=strtobool(enabled))

        if adapter_code:
            filter_qs &= Q(adapter_code=adapter_code)

        if name_search_string:
            name_search_string = str(name_search_string).strip()
            filter_qs &= Q(name__icontains=name_search_string)

        if not capability:
            if (
                entity_type
                and entity_type.lower() == "invoice"
                and (
                    supports_import
                    and supports_import is True
                    or supports_import == "true"
                )
            ):
                capability = "invoice.download"

        if capability:
            filter_qs &= Q(capabilities__type=capability)

        show_hidden = strtobool(show_hidden)
        if not show_hidden:
            filter_qs &= Q(hidden=False)

        queryset = queryset.filter(filter_qs).distinct()

        return queryset
