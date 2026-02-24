from dal import autocomplete
from django.conf import settings
from django.db.models import Q
from django.views.generic import TemplateView
from spices.django3.accounts.models import BearerToken
from spices.django3.coreobjects.base import (
    SharedCoreObjectModel,
    COREOBJECTS_PREFIX_REGISTRY,
)
from spices.django3.coreobjects.models import Location
from spices.http_utils import get_new_retryable_session_500

from integrator import LOGGER


class HomePageView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        token = (
            BearerToken.objects.filter(user=self.request.user)
            .order_by("-created_date")
            .first()
        )
        context["token"] = token
        return context


class CoreObjectsAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete API for SharedCoreObjectModel"""

    paginate_by = 100

    def get_queryset(self):
        """Get filtered queryset for request"""
        if not self.request.user.is_staff:
            # for now, restrict to staff only, disallow other authenticated users
            return SharedCoreObjectModel.objects.none()

        queryset = SharedCoreObjectModel.objects.all().order_by("-display_name")
        object_type = self.forwarded.get("type")
        if object_type:
            queryset = queryset.filter(type=object_type)

        model = COREOBJECTS_PREFIX_REGISTRY[object_type]

        if self.q:
            queryset = queryset.filter(
                Q(display_name__icontains=self.q)
                | Q(remote_id__icontains=self.q)
                | Q(id__icontains=self.q)
            )

            params = {
                "limit": self.paginate_by,
            }
            if self.request.GET.get("page"):
                params["page"] = self.request.GET.get("page")

            # TODO: Bug in server, restaurant API crashes on query search. Has to be fixed separately
            if model == Location:
                params["name"] = self.q
            else:
                params["query"] = self.q

            session = get_new_retryable_session_500(
                retries_count=5, raise_on_status=False
            )
            url = f"{settings.PIQ_API_URL}{model.endpoint}/"
            response = session.get(
                url,
                headers={"Authorization": f"Token {settings.PIQ_API_TOKEN}"},
                params=params,
            )

            LOGGER.info(
                f"[tag:WIVCOAL10] Search {model.endpoint} API returned response {response.status_code} "
                f"when queried with params: {params}."
            )

            if response.ok:
                response = response.json()
                if not isinstance(response, list):
                    response = response.get("results", [])

                LOGGER.debug(
                    f"[tag:WIVCOAL20] Caching {len(response)} objects returned from {model.endpoint} API."
                )
                for json_obj in response:
                    model.objects.get_or_create(
                        defaults={
                            "url": json_obj["url"],
                            "display_name": json_obj.get(
                                "display_name", json_obj.get("name")
                            ),
                        },
                        remote_id=json_obj["id"],
                        type=object_type,
                    )

        return queryset
