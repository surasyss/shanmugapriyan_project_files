"""apps URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from spices.django3.auth.views import OAuthLoginView, OAuthLogoutView

from apps.definitions.urls import definitions_router
from apps.jobconfig.urls import jobconfig_router
from apps.runs.urls import runs_router
from .views import HomePageView, CoreObjectsAutocomplete

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", login_required(HomePageView.as_view())),
    path("accounts/login/", OAuthLoginView.as_view(), name="login"),
    path(
        "accounts/admin/login/", OAuthLoginView.as_view(admin=True), name="admin-login"
    ),
    path("logout", OAuthLogoutView.as_view(), name="logout"),
    path("api/definitions/", include(definitions_router.urls)),
    path("api/jobconfig/", include(jobconfig_router.urls)),
    path("api/runs/", include(runs_router.urls)),
    url(
        r"^coreobjects-autocomplete/$",
        login_required(CoreObjectsAutocomplete.as_view()),
        name="coreobjects-autocomplete",
    ),
]

admin.site.login = OAuthLoginView.as_view(admin=True)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
