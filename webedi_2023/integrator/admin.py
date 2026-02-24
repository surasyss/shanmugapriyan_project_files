from django.conf import settings
from django.contrib import admin

from spices.django3.accounts.views import OAuthLoginView

admin.site.login = OAuthLoginView.as_view(admin=True)
admin.site.site_header = settings.DJANGO_ADMIN_SITE_HEADER

if not settings.DJANGO_ADMIN_ALLOW_DELETE:
    admin.site.disable_action("delete_selected")
