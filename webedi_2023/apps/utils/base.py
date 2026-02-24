import json

from django.conf import settings
from django.core.cache import cache
from django.views.decorators.cache import never_cache

from spices.django3.auth.base_view import BaseAuthenticatedView

_SENTINEL = object()


class AccountAuthenticatedApiView(BaseAuthenticatedView):
    """
    Authenticates API based on user's account_ids
    """

    allow_staff_access = False
    acl_field = None
    account_ids = None

    @never_cache
    def dispatch(self, request, *args, **kwargs):
        """override to apply the never_cache decorator"""
        return super().dispatch(request, *args, **kwargs)

    def _fetch_account_ids(self):
        """Get all unique Restaurant Account IDs for a user"""
        cache_key = f"usr:acc_ids:{self.request.user.id}"
        value: str = cache.get(cache_key, _SENTINEL)
        if value == _SENTINEL:
            auth_header = self.request.headers["Authorization"]
            account_ids = settings.PIQ_CORE_CLIENT.get_accessible_account_ids_for(
                auth_header
            )
            value: str = json.dumps(account_ids)
            cache.set(cache_key, value, 3600)

        self.account_ids = json.loads(value)

    def perform_authentication(self, request):
        super().perform_authentication(request)
        self._fetch_account_ids()

    def apply_acl_filter(self, queryset):
        """Returns Queryset after applying ACL filters"""
        if self.request.user.is_staff and self.allow_staff_access:
            return queryset

        if self.request.user.is_worker:
            return queryset

        # noinspection PyProtectedMember
        fields = [f.name for f in queryset.model._meta.get_fields()]
        if hasattr(self, "acl_field") and self.acl_field:
            acl_field = self.acl_field
        elif (
            settings.PIQ_DEFAULT_AUTH_COLUMN
            and settings.PIQ_DEFAULT_AUTH_COLUMN in fields
        ):
            acl_field = settings.PIQ_DEFAULT_AUTH_COLUMN
        else:
            raise Exception(
                "No ACL field found. Re-Implement apply_acl_filter or declare a acl_field"
            )

        return queryset.filter(**{acl_field + "__remote_id__in": self.account_ids})
